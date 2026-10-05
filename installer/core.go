package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

var runtimeNames = []string{"pakchunk1015-Windows_P.pak", "pakchunk1015-Windows_P.utoc", "pakchunk1015-Windows_P.ucas"}

var steamPayloadEditionID = "Steam_current"

type edition struct {
	ID, Label, Note string
	Files           []string
}

var editions = []edition{
	{steamPayloadEditionID, "Steam", "Русификатор 18.6 TEST для Steam. Исправлена запись текста эссенции; запуск требует проверки. Исходная версия игры: 0.7.9.16321.", runtimeNames},
	{"NoSteam_0.7.9.16232", "NoSteam 0.7.9.16232", "Полный комплект для исходной NoSteam 0.7.9.16232.", runtimeNames},
	{"NoSteam_0.7.9.16313plus", "NoSteam 0.7.9.16313 / 16315+", "Использует актуальный совместимый Steam_current комплект. NoSteam 0.7.9.16232 всегда остаётся отдельным payload.", runtimeNames},
}

func payloadEdition(e edition) string {
	if e.ID == "NoSteam_0.7.9.16313plus" {
		return editions[0].ID
	}
	return e.ID
}

const stateName = "CI_RU_Installed.json"

type fileRecord struct {
	Name   string `json:"name"`
	SHA256 string `json:"sha256"`
}
type installedState struct {
	Edition             string       `json:"edition"`
	Mode                string       `json:"install_mode,omitempty"`
	InstalledAt         string       `json:"installed_at"`
	Backup              string       `json:"backup,omitempty"`
	Files               []fileRecord `json:"files"`
	BackupFiles         []fileRecord `json:"backup_files,omitempty"`
	PreviousStateSHA256 string       `json:"previous_state_sha256,omitempty"`
}
type payloadFile struct {
	fileRecord
	Data []byte
}
type installPlan struct {
	Root, Paks string
	Edition    edition
	Files      []payloadFile
	Trusted    map[string]map[string]bool
	Existing   map[string]string
	OldState   []byte
}

func locatePaks(input string) (string, string, error) {
	input = strings.TrimSpace(strings.Trim(input, "\""))
	if input == "" {
		return "", "", errors.New("выберите папку игры")
	}
	abs, err := filepath.Abs(input)
	if err != nil {
		return "", "", err
	}
	paths := []string{abs, filepath.Join(abs, "Content", "Paks"), filepath.Join(abs, "Carnal_Instinct_UE5", "Content", "Paks")}
	if strings.EqualFold(filepath.Base(abs), "Content") {
		paths = append(paths, filepath.Join(abs, "Paks"))
	}
	for _, p := range paths {
		if !strings.EqualFold(filepath.Base(p), "Paks") || !strings.EqualFold(filepath.Base(filepath.Dir(p)), "Content") {
			continue
		}
		if st, e := os.Stat(p); e == nil && st.IsDir() {
			resolved, e := filepath.EvalSymlinks(p)
			if e != nil {
				return "", "", e
			}
			if !strings.EqualFold(filepath.Base(resolved), "Paks") || !strings.EqualFold(filepath.Base(filepath.Dir(resolved)), "Content") {
				continue
			}
			root := filepath.Dir(filepath.Dir(resolved))
			if !isGameRoot(root) {
				continue
			}
			return root, resolved, nil
		}
	}
	return "", "", errors.New("не найдена папка Content\\Paks игры Carnal Instinct; укажите папку игры или Carnal_Instinct_UE5")
}

func isGameRoot(root string) bool {
	if strings.EqualFold(filepath.Base(root), "Carnal_Instinct_UE5") {
		return true
	}
	for _, name := range []string{"Carnal_Instinct_UE5.exe", filepath.Join("Binaries", "Win64", "Carnal_Instinct_UE5-Win64-Shipping.exe")} {
		if st, e := os.Lstat(filepath.Join(root, name)); e == nil && st.Mode().IsRegular() {
			return true
		}
	}
	return false
}

func bytesHash(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func fileHash(p string) (string, error) {
	st, err := os.Lstat(p)
	if err != nil {
		return "", err
	}
	if !st.Mode().IsRegular() {
		return "", fmt.Errorf("необычный тип файла: %s", p)
	}
	f, err := os.Open(p)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err = io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
func validateState(b []byte) (installedState, error) {
	var state installedState
	if err := json.Unmarshal(b, &state); err != nil {
		return state, fmt.Errorf("повреждена запись установки: %w", err)
	}
	validEdition := false
	for _, e := range editions {
		if e.ID == state.Edition {
			validEdition = true
		}
	}
	if !validEdition || len(state.Files) != 3 {
		return state, errors.New("неизвестный комплект в записи установки")
	}
	if state.Mode != "" && state.Mode != "replace" {
		return state, errors.New("неизвестный режим установки")
	}
	if state.Mode == "replace" && (state.Backup != "" || len(state.BackupFiles) > 0 || state.PreviousStateSHA256 != "") {
		return state, errors.New("неверная запись замены")
	}
	if state.Mode != "replace" && state.BackupFiles == nil {
		return state, errors.New("в записи установки отсутствует список резервных копий; автоматическое изменение файлов остановлено")
	}
	seen := map[string]bool{}
	for _, f := range state.Files {
		allowed := false
		for _, n := range runtimeNames {
			if n == f.Name {
				allowed = true
			}
		}
		_, err := hex.DecodeString(f.SHA256)
		if !allowed || seen[f.Name] || len(f.SHA256) != 64 || err != nil {
			return state, errors.New("неверные файлы в записи установки")
		}
		seen[f.Name] = true
	}
	seen = map[string]bool{}
	for _, f := range state.BackupFiles {
		allowed := false
		for _, n := range runtimeNames {
			if n == f.Name {
				allowed = true
			}
		}
		_, e := hex.DecodeString(f.SHA256)
		if !allowed || seen[f.Name] || len(f.SHA256) != 64 || e != nil {
			return state, errors.New("повреждена запись резервной копии")
		}
		seen[f.Name] = true
	}
	if state.PreviousStateSHA256 != "" {
		if _, e := hex.DecodeString(state.PreviousStateSHA256); e != nil || len(state.PreviousStateSHA256) != 64 {
			return state, errors.New("повреждена контрольная сумма прежней записи")
		}
	}
	if state.Mode != "replace" && (state.Backup == "" || filepath.Base(state.Backup) != state.Backup || strings.ContainsAny(state.Backup, "/\\<>:\"|?*\x00") || state.Backup == "." || state.Backup == ".." || strings.TrimRight(state.Backup, " .") != state.Backup) {
		return state, errors.New("неверный путь резервной копии")
	}
	return state, nil
}
func readState(root string) ([]byte, error) {
	p := filepath.Join(root, stateName)
	if _, e := os.Lstat(p); os.IsNotExist(e) {
		return nil, nil
	}
	if _, e := fileHash(p); e != nil {
		return nil, e
	}
	b, e := os.ReadFile(p)
	if e != nil {
		return nil, e
	}
	if _, e = validateState(b); e != nil {
		return nil, e
	}
	return b, nil
}

func prepareInstall(source fs.FS, selected edition, input string) (installPlan, error) {
	p := installPlan{Edition: selected, Existing: map[string]string{}}
	var err error
	p.Root, p.Paks, err = locatePaks(input)
	if err != nil {
		return p, err
	}
	registered := false
	for _, e := range editions {
		if e.ID == selected.ID {
			registered = true
			selected = e
			p.Edition = e
			break
		}
	}
	if !registered {
		return p, errors.New("не выбрана поддерживаемая версия")
	}
	for _, n := range selected.Files {
		b, e := fs.ReadFile(source, "payload/"+payloadEdition(selected)+"/"+n)
		if e != nil {
			return p, fmt.Errorf("не удалось прочитать встроенный комплект: %w", e)
		}
		p.Files = append(p.Files, payloadFile{fileRecord{n, bytesHash(b)}, b})
	}
	p.OldState, err = readState(p.Root)
	if err != nil {
		return p, err
	}
	known := map[string]map[string]bool{}
	for _, n := range runtimeNames {
		known[n] = map[string]bool{}
	}
	if b, e := fs.ReadFile(source, "trusted_hashes.json"); e == nil {
		var hashes map[string][]string
		if e = json.Unmarshal(b, &hashes); e != nil {
			return p, e
		}
		for n, hs := range hashes {
			if known[n] != nil {
				for _, h := range hs {
					known[n][h] = true
				}
			}
		}
	}
	for _, e := range editions {
		for _, n := range e.Files {
			if b, err := fs.ReadFile(source, "payload/"+e.ID+"/"+n); err == nil {
				known[n][bytesHash(b)] = true
			}
		}
	}
	if len(p.OldState) > 0 {
		state, _ := validateState(p.OldState)
		for _, f := range append(append([]fileRecord{}, state.Files...), state.BackupFiles...) {
			known[f.Name][f.SHA256] = true
		}
	}
	for _, n := range runtimeNames {
		h, e := fileHash(filepath.Join(p.Paks, n))
		if os.IsNotExist(e) {
			continue
		}
		if e != nil {
			return p, e
		}
		if !known[n][h] {
			return p, fmt.Errorf("%s отличается от известных файлов русификации. Переместите этот сторонний файл из Paks перед установкой", n)
		}
		p.Existing[n] = h
	}
	p.Trusted = known
	return p, nil
}

// The creation result lets callers remove their own partial file on a write error.
// Tests replace this operation to reproduce disk and exclusive-creation failures.
var writeExclusiveFile = createExclusiveFile

func createExclusiveFile(p string, b []byte) (created bool, err error) {
	f, e := os.OpenFile(p, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if e != nil {
		return false, e
	}
	_, err = f.Write(b)
	if err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err == nil {
		err = closeErr
	}
	return true, err
}
func writeFile(p string, b []byte) error {
	_, e := writeExclusiveFile(p, b)
	return e
}
func copyFile(src, dst string) error {
	b, e := os.ReadFile(src)
	if e != nil {
		return e
	}
	f, e := os.OpenFile(dst, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if e != nil {
		return e
	}
	_, e = f.Write(b)
	if e == nil {
		e = f.Sync()
	}
	ce := f.Close()
	if e == nil {
		e = ce
	}
	return e
}
func removeOwnedFile(p, expectedHash string) error {
	h, e := fileHash(p)
	if os.IsNotExist(e) {
		return nil
	}
	if e != nil {
		return e
	}
	if expectedHash == "" || h != expectedHash {
		return fmt.Errorf("файл изменён другим процессом и сохранён без изменений: %s", p)
	}
	return os.Remove(p)
}

// A hard link publishes the held original without replacing an occupied path.
// Filesystems without hard links use exclusive creation, retaining the held
// original if that copy fails. Recovery never depends on deleting the source.
func restoreHeldFile(src, dst string) error {
	if err := os.Link(src, dst); err == nil {
		return nil
	}
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	if _, err = createExclusiveFile(dst, data); err != nil {
		return err
	}
	hash, err := fileHash(dst)
	if err != nil {
		return err
	}
	if hash != bytesHash(data) {
		return fmt.Errorf("восстановленный файл изменён другим процессом: %s", dst)
	}
	return nil
}
func sameCurrent(p installPlan) error {
	for _, n := range runtimeNames {
		h, e := fileHash(filepath.Join(p.Paks, n))
		if os.IsNotExist(e) {
			if p.Existing[n] != "" {
				return fmt.Errorf("файл изменён после проверки: %s", n)
			}
			continue
		}
		if e != nil {
			return e
		}
		if h != p.Existing[n] {
			return fmt.Errorf("файл изменён после проверки: %s", n)
		}
	}
	b, e := readState(p.Root)
	if e != nil {
		return e
	}
	if string(b) != string(p.OldState) {
		return errors.New("запись установки изменилась после проверки")
	}
	return nil
}

func install(p installPlan, progress func(string)) (backup string, err error) {
	report := func(s string) {
		if progress != nil {
			progress(s)
		}
	}
	if err = sameCurrent(p); err != nil {
		return "", err
	}
	stage, err := os.MkdirTemp(p.Paks, ".ci-ru-stage-")
	if err != nil {
		return "", err
	}
	defer os.RemoveAll(stage)
	for _, it := range p.Files {
		target := filepath.Join(stage, it.Name)
		if err = writeFile(target, it.Data); err != nil {
			return "", err
		}
		h, e := fileHash(target)
		if e != nil {
			return "", e
		}
		if h != it.SHA256 {
			return "", errors.New("не совпала контрольная сумма подготовленного файла")
		}
	}
	// Old file contents are kept in memory only while replacing the payload.
	state := installedState{Edition: p.Edition.ID, Mode: "replace", InstalledAt: time.Now().Format(time.RFC3339)}
	for _, it := range p.Files {
		state.Files = append(state.Files, it.fileRecord)
	}
	stateData, e := json.MarshalIndent(state, "", "  ")
	if e != nil {
		return backup, e
	}
	if err = writeFile(filepath.Join(stage, stateName), stateData); err != nil {
		return backup, err
	}
	if err = sameCurrent(p); err != nil {
		return backup, err
	}
	changed := []string{}
	held := map[string][]byte{}
	written := map[string]bool{}
	writtenHashes := map[string]string{}
	stateChanged := false
	stateWritten := false
	stateWrittenHash := ""
	var heldState []byte
	committed := false
	defer func() {
		if committed {
			return
		}
		var restoreErrors []error
		for _, n := range changed {
			dest := filepath.Join(p.Paks, n)
			if written[n] {
				if e := removeOwnedFile(dest, writtenHashes[n]); e != nil {
					restoreErrors = append(restoreErrors, e)
				}
			}
			if src := held[n]; src != nil {
				if _, e := os.Lstat(dest); os.IsNotExist(e) {
					if _, e := createExclusiveFile(dest, src); e != nil {
						restoreErrors = append(restoreErrors, e)
					}
				} else {
					restoreErrors = append(restoreErrors, fmt.Errorf("не удалось вернуть %s: целевой путь уже занят", n))
				}
			}
		}
		if stateChanged {
			dest := filepath.Join(p.Root, stateName)
			if stateWritten {
				if e := removeOwnedFile(dest, stateWrittenHash); e != nil {
					restoreErrors = append(restoreErrors, e)
				}
			}
			if heldState != nil {
				if _, e := os.Lstat(dest); os.IsNotExist(e) {
					if _, e := createExclusiveFile(dest, heldState); e != nil {
						restoreErrors = append(restoreErrors, e)
					}
				} else {
					restoreErrors = append(restoreErrors, errors.New("путь прежней записи установки занят другим процессом"))
				}
			}
		}
		if len(restoreErrors) > 0 {
			err = errors.Join(err, fmt.Errorf("ошибка отмены замены: %w", errors.Join(restoreErrors...)))
		}
	}()
	for _, it := range p.Files {
		report("Установка: " + it.Name)
		dest := filepath.Join(p.Paks, it.Name)
		h, e := fileHash(dest)
		if e != nil && !os.IsNotExist(e) {
			return backup, e
		}
		if h != p.Existing[it.Name] {
			return backup, fmt.Errorf("файл изменён во время установки: %s", it.Name)
		}
		oldRecord, e := readState(p.Root)
		if e != nil {
			return backup, e
		}
		if string(oldRecord) != string(p.OldState) {
			return backup, errors.New("запись установки изменена другим процессом")
		}
		changed = append(changed, it.Name)
		if p.Existing[it.Name] != "" {
			oldData, readErr := os.ReadFile(dest)
			if readErr != nil {
				return "", readErr
			}
			if bytesHash(oldData) != p.Existing[it.Name] {
				return "", errors.New("исходный файл изменился во время проверки")
			}
			if err = removeOwnedFile(dest, p.Existing[it.Name]); err != nil {
				return "", err
			}
			held[it.Name] = oldData
		}
		// Exclusive creation never overwrites a file placed by another process.
		created, writeErr := writeExclusiveFile(dest, it.Data)
		if created {
			written[it.Name] = true
			h, e = fileHash(dest)
			if e == nil {
				writtenHashes[it.Name] = h
			}
		}
		if writeErr != nil {
			return backup, writeErr
		}
		if e != nil {
			return backup, e
		}
		if !created || h != it.SHA256 {
			return backup, fmt.Errorf("контрольная сумма не совпала: %s", it.Name)
		}
	}
	for _, it := range p.Files {
		h, e := fileHash(filepath.Join(p.Paks, it.Name))
		if e != nil {
			return backup, e
		}
		if h != it.SHA256 {
			return backup, fmt.Errorf("файл изменён во время установки: %s", it.Name)
		}
	}
	oldRecord, e := readState(p.Root)
	if e != nil {
		return backup, e
	}
	if string(oldRecord) != string(p.OldState) {
		return backup, errors.New("запись установки изменена другим процессом")
	}
	if len(p.OldState) > 0 {
		if err = removeOwnedFile(filepath.Join(p.Root, stateName), bytesHash(p.OldState)); err != nil {
			return "", err
		}
		heldState = append([]byte{}, p.OldState...)
		stateChanged = true
	}
	created, writeErr := writeExclusiveFile(filepath.Join(p.Root, stateName), stateData)
	if created {
		stateChanged = true
		stateWritten = true
		stateWrittenHash, _ = fileHash(filepath.Join(p.Root, stateName))
	}
	if writeErr != nil {
		return backup, writeErr
	}
	if !created || stateWrittenHash != bytesHash(stateData) {
		return backup, errors.New("не совпала контрольная сумма записи установки")
	}
	committed = true
	report("Очистка старых копий русификации…")
	if err = cleanupLegacyBackups(p.Root, p.Trusted); err != nil {
		return "", fmt.Errorf("русификация установлена; очистка старых копий не завершена: %w", err)
	}
	return "", nil
}

// Delete only recognized localization files; do not follow links or remove
// unrelated files from a backup folder. Never create backup directories.
func cleanupLegacyBackupTree(base, previous string, known map[string]map[string]bool) error {
	for _, folder := range []string{base, previous} {
		st, err := os.Lstat(folder)
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return nil
		}
	}
	dirs, err := os.ReadDir(previous)
	if err != nil {
		return err
	}
	for _, dir := range dirs {
		if !dir.IsDir() || dir.Type()&os.ModeSymlink != 0 {
			continue
		}
		folder := filepath.Join(previous, dir.Name())
		local := map[string]map[string]bool{}
		for _, n := range runtimeNames {
			local[n] = map[string]bool{}
			for h := range known[n] {
				local[n][h] = true
			}
		}
		manifests := map[string]string{}
		for _, n := range []string{"previous_state.json", "held_previous_state.json"} {
			path := filepath.Join(folder, n)
			h, e := fileHash(path)
			if e != nil {
				continue
			}
			b, e := os.ReadFile(path)
			if e != nil {
				return e
			}
			state, e := validateState(b)
			if e != nil {
				continue
			}
			manifests[n] = h
			for _, f := range append(append([]fileRecord{}, state.Files...), state.BackupFiles...) {
				local[f.Name][f.SHA256] = true
			}
		}
		ownedNames := append(append([]string{}, runtimeNames...), "RussianTranslation_P.pak", "RussianTranslation_P.utoc", "RussianTranslation_P.ucas")
		for _, n := range ownedNames {
			for _, candidate := range []string{n, "held_" + n} {
				path := filepath.Join(folder, candidate)
				h, e := fileHash(path)
				if e != nil {
					continue
				}
				if local[n][h] || regexp.MustCompile(`^\d{8}_\d{6}(_\d+)?$`).MatchString(dir.Name()) {
					if e = removeOwnedFile(path, h); e != nil {
						return e
					}
				}
			}
		}
		for n, h := range manifests {
			if err = removeOwnedFile(filepath.Join(folder, n), h); err != nil {
				return err
			}
		}
		entries, e := os.ReadDir(folder)
		if e != nil {
			return e
		}
		if len(entries) == 0 {
			if e = os.Remove(folder); e != nil {
				return e
			}
		}
	}
	for _, folder := range []string{previous, base} {
		entries, e := os.ReadDir(folder)
		if os.IsNotExist(e) {
			continue
		}
		if e != nil {
			return e
		}
		if len(entries) == 0 {
			if e = os.Remove(folder); e != nil {
				return e
			}
		}
	}
	return nil
}

func uninstall(input string, progress func(string)) (err error) {
	root, paks, err := locatePaks(input)
	if err != nil {
		return err
	}
	b, err := readState(root)
	if err != nil {
		return err
	}
	if len(b) == 0 {
		return errors.New("не найдена запись установки; файлы без записи автоматически не удаляются")
	}
	state, err := validateState(b)
	if err != nil {
		return err
	}
	originals := map[string][]byte{}
	known := map[string]map[string]bool{}
	for _, f := range state.Files {
		path := filepath.Join(paks, f.Name)
		h, e := fileHash(path)
		if e != nil {
			return e
		}
		if h != f.SHA256 {
			return fmt.Errorf("%s изменён после установки; удаление остановлено", f.Name)
		}
		data, e := os.ReadFile(path)
		if e != nil {
			return e
		}
		if bytesHash(data) != h {
			return errors.New("файл изменён во время проверки удаления")
		}
		originals[f.Name] = data
		known[f.Name] = map[string]bool{h: true}
	}
	for _, f := range state.BackupFiles {
		known[f.Name][f.SHA256] = true
	}
	removed := map[string]bool{}
	committed := false
	defer func() {
		if committed {
			return
		}
		var es []error
		for n := range removed {
			if _, e := createExclusiveFile(filepath.Join(paks, n), originals[n]); e != nil {
				es = append(es, e)
			}
		}
		if len(es) > 0 {
			err = errors.Join(err, fmt.Errorf("не удалось полностью отменить удаление: %w", errors.Join(es...)))
		}
	}()
	for _, f := range state.Files {
		if progress != nil {
			progress("Удаление: " + f.Name)
		}
		current, e := readState(root)
		if e != nil {
			return e
		}
		if string(current) != string(b) {
			return errors.New("запись установки изменена другим процессом")
		}
		if err = removeOwnedFile(filepath.Join(paks, f.Name), f.SHA256); err != nil {
			return err
		}
		removed[f.Name] = true
	}
	current, e := readState(root)
	if e != nil {
		return e
	}
	if string(current) != string(b) {
		return errors.New("запись установки изменена другим процессом")
	}
	if err = removeOwnedFile(filepath.Join(root, stateName), bytesHash(b)); err != nil {
		return err
	}
	committed = true
	return cleanupLegacyBackups(root, known)
}

func cleanupLegacyBackups(root string, known map[string]map[string]bool) error {
	base := filepath.Join(root, "CI_RU_Backup")
	if err := cleanupLegacyBackupTree(base, filepath.Join(base, "Previous"), known); err != nil {
		return err
	}
	for _, parent := range []string{root, filepath.Dir(root)} {
		for _, name := range []string{"RU_DontLook_Backup", "RU_DontLook_Removed"} {
			folder := filepath.Join(parent, name)
			if err := cleanupLegacyBackupTree(folder, folder, known); err != nil {
				return err
			}
		}
	}
	paks := filepath.Join(root, "Content", "Paks")
	for _, name := range runtimeNames {
		for _, suffix := range []string{".bak", ".backup", ".old"} {
			path := filepath.Join(paks, name+suffix)
			h, err := fileHash(path)
			if err != nil {
				continue
			}
			if known[name][h] {
				if err = removeOwnedFile(path, h); err != nil {
					return err
				}
			}
		}
	}
	return nil
}
