package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"testing"
	"testing/fstest"
)

func fixture(t *testing.T) (string, fs.FS) {
	t.Helper()
	root := filepath.Join(t.TempDir(), "Carnal_Instinct_UE5")
	if err := os.MkdirAll(filepath.Join(root, "Content", "Paks"), 0755); err != nil {
		t.Fatal(err)
	}
	data := fstest.MapFS{}
	for _, edition := range editions {
		for _, name := range edition.Files {
			data["payload/"+payloadEdition(edition)+"/"+name] = &fstest.MapFile{Data: []byte(payloadEdition(edition) + "/" + name)}
		}
	}
	return root, data
}

func TestSteamDisplayLabelShowsVerifiedGameVersionAndStablePayloadID(t *testing.T) {
	if editions[0].Label != "Steam" {
		t.Fatalf("Steam label must not expose game version: %q", editions[0].Label)
	}
	if editions[0].ID != "Steam_current" {
		t.Fatalf("Steam payload ID must remain rolling/stable: %q", editions[0].ID)
	}
}

func TestNewNoSteamAlwaysUsesCurrentSteamFullPayload(t *testing.T) {
	root, data := fixture(t)
	plan, err := prepareInstall(data, editions[2], root)
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Files) != 3 {
		t.Fatal("new NoSteam must use a complete payload")
	}
	if _, err = install(plan, nil); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(filepath.Join(plan.Paks, runtimeNames[0]))
	if err != nil {
		t.Fatal(err)
	}
	want := editions[0].ID + "/" + runtimeNames[0]
	if string(got) != want {
		t.Fatalf("wrong edition payload: %s", got)
	}
	for _, name := range runtimeNames[1:] {
		b, e := os.ReadFile(filepath.Join(plan.Paks, name))
		if e != nil {
			t.Fatal(e)
		}
		if string(b) != editions[0].ID+"/"+name {
			t.Fatalf("wrong binary edition payload: %s", name)
		}
	}
}

func TestChangedInstalledFileStopsRemovalWithoutDeletingAnyFile(t *testing.T) {
	root, data := fixture(t)
	p, e := prepareInstall(data, editions[0], root)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = install(p, nil); e != nil {
		t.Fatal(e)
	}
	if e = os.WriteFile(filepath.Join(p.Paks, runtimeNames[1]), []byte("user changed"), 0644); e != nil {
		t.Fatal(e)
	}
	if e = uninstall(root, nil); e == nil {
		t.Fatal("uninstall accepted changed file")
	}
	for _, n := range runtimeNames {
		if _, e = os.Stat(filepath.Join(p.Paks, n)); e != nil {
			t.Fatal("removed file on failed validation", n)
		}
	}
}

func TestUntrackedFileIsNotOverwritten(t *testing.T) {
	root, data := fixture(t)
	p := filepath.Join(root, "Content", "Paks", runtimeNames[0])
	if e := os.WriteFile(p, []byte("unrelated container"), 0644); e != nil {
		t.Fatal(e)
	}
	if _, e := prepareInstall(data, editions[0], root); e == nil {
		t.Fatal("unknown file accepted")
	}
	b, _ := os.ReadFile(p)
	if string(b) != "unrelated container" {
		t.Fatal("unknown file changed")
	}
}

func TestMissingPayloadDoesNotTouchGame(t *testing.T) {
	root, data := fixture(t)
	delete(data.(fstest.MapFS), "payload/"+editions[0].ID+"/"+runtimeNames[1])
	if _, e := prepareInstall(data, editions[0], root); e == nil {
		t.Fatal("incomplete payload accepted")
	}
	files, _ := os.ReadDir(filepath.Join(root, "Content", "Paks"))
	if len(files) != 0 {
		t.Fatal("game modified by preflight")
	}
}

func TestInvalidPaksParentIsRejected(t *testing.T) {
	root := t.TempDir()
	if e := os.MkdirAll(filepath.Join(root, "wrong", "Paks"), 0755); e != nil {
		t.Fatal(e)
	}
	if _, _, e := locatePaks(filepath.Join(root, "wrong", "Paks")); e == nil {
		t.Fatal("non-Content Paks accepted")
	}
}

func installEdition(t *testing.T, root string, data fs.FS, selected edition) (installPlan, string) {
	t.Helper()
	p, e := prepareInstall(data, selected, root)
	if e != nil {
		t.Fatal(e)
	}
	backup, e := install(p, nil)
	if e != nil {
		t.Fatal(e)
	}
	return p, backup
}

func installedSnapshot(t *testing.T, p installPlan) map[string][]byte {
	t.Helper()
	snapshot := map[string][]byte{}
	for _, n := range append(append([]string{}, runtimeNames...), stateName) {
		path := filepath.Join(p.Paks, n)
		if n == stateName {
			path = filepath.Join(p.Root, n)
		}
		b, e := os.ReadFile(path)
		if e != nil {
			t.Fatal(e)
		}
		snapshot[path] = b
	}
	return snapshot
}

func assertSnapshot(t *testing.T, snapshot map[string][]byte) {
	t.Helper()
	for path, want := range snapshot {
		got, e := os.ReadFile(path)
		if e != nil {
			t.Fatal(e)
		}
		if !bytes.Equal(got, want) {
			t.Fatalf("file changed: %s", path)
		}
	}
}

func assertPayload(t *testing.T, p installPlan, data fs.FS, payloadID string) {
	t.Helper()
	for _, n := range runtimeNames {
		want, e := fs.ReadFile(data, "payload/"+payloadID+"/"+n)
		if e != nil {
			t.Fatal(e)
		}
		got, e := os.ReadFile(filepath.Join(p.Paks, n))
		if e != nil {
			t.Fatal(e)
		}
		if !bytes.Equal(got, want) {
			t.Fatalf("wrong payload for %s", n)
		}
	}
}

func TestGameDirectoryIsRecognizedBeforeInstalling(t *testing.T) {
	for _, tc := range []struct {
		name, marker string
		want         bool
	}{
		{"unrelated game", "", false},
		{"matching launcher", "Carnal_Instinct_UE5.exe", true},
		{"matching shipping exe", filepath.Join("Binaries", "Win64", "Carnal_Instinct_UE5-Win64-Shipping.exe"), true},
		{"other launcher", "OtherGame.exe", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := filepath.Join(t.TempDir(), "OtherGame")
			if e := os.MkdirAll(filepath.Join(root, "Content", "Paks"), 0755); e != nil {
				t.Fatal(e)
			}
			if tc.marker != "" {
				p := filepath.Join(root, tc.marker)
				if e := os.MkdirAll(filepath.Dir(p), 0755); e != nil {
					t.Fatal(e)
				}
				if e := os.WriteFile(p, []byte("exe marker"), 0644); e != nil {
					t.Fatal(e)
				}
			}
			for _, input := range []string{root, filepath.Join(root, "Content"), filepath.Join(root, "Content", "Paks")} {
				got, _, e := locatePaks(input)
				if tc.want {
					if e != nil || got != root {
						t.Fatalf("matching game rejected: %s: %v", input, e)
					}
				} else if e == nil {
					t.Fatalf("unrelated game accepted: %s", input)
				}
			}
		})
	}
	root, _ := fixture(t)
	for _, input := range []string{root, filepath.Dir(root), filepath.Join(root, "Content"), filepath.Join(root, "Content", "Paks")} {
		if _, _, e := locatePaks(input); e != nil {
			t.Fatalf("canonical game rejected: %s: %v", input, e)
		}
	}
}

func TestMatchingExecutableDirectoryIsNotGameMarker(t *testing.T) {
	root := filepath.Join(t.TempDir(), "OtherGame")
	for _, p := range []string{filepath.Join(root, "Content", "Paks"), filepath.Join(root, "Carnal_Instinct_UE5.exe")} {
		if e := os.MkdirAll(p, 0755); e != nil {
			t.Fatal(e)
		}
	}
	if _, _, e := locatePaks(root); e == nil {
		t.Fatal("directory was accepted as game executable")
	}
}

func TestNewNoSteamUsesUpdatedSteamPayload(t *testing.T) {
	root, data := fixture(t)
	installEdition(t, root, data, editions[2])
	for _, n := range runtimeNames {
		data.(fstest.MapFS)["payload/"+editions[0].ID+"/"+n] = &fstest.MapFile{Data: []byte("updated Steam/" + n)}
		data.(fstest.MapFS)["payload/"+editions[2].ID+"/"+n] = &fstest.MapFile{Data: []byte("stale separate NoSteam/" + n)}
	}
	p, _ := installEdition(t, root, data, editions[2])
	assertPayload(t, p, data, editions[0].ID)
	if err := uninstall(root, nil); err != nil {
		t.Fatal(err)
	}
	for _, n := range runtimeNames {
		if _, err := os.Lstat(filepath.Join(p.Paks, n)); !os.IsNotExist(err) {
			t.Fatal("previous translation restored", n)
		}
	}
}

func TestOldNoSteamUsesItsOwnPayload(t *testing.T) {
	root, data := fixture(t)
	for _, n := range runtimeNames {
		data.(fstest.MapFS)["payload/"+editions[0].ID+"/"+n] = &fstest.MapFile{Data: []byte("updated Steam/" + n)}
	}
	p, _ := installEdition(t, root, data, editions[1])
	assertPayload(t, p, data, editions[1].ID)
}

func TestNewNoSteamTracksFutureContentInStableSteamCurrentFolder(t *testing.T) {
	root, data := fixture(t)
	installEdition(t, root, data, editions[2])
	for _, n := range runtimeNames {
		data.(fstest.MapFS)["payload/Steam_current/"+n] = &fstest.MapFile{Data: []byte("future Steam/" + n)}
	}
	p, _ := installEdition(t, root, data, editions[2])
	assertPayload(t, p, data, "Steam_current")
}

func TestRegisteredEditionUsesOnlyCanonicalRuntimeFiles(t *testing.T) {
	root, data := fixture(t)
	selected := edition{ID: editions[0].ID, Files: []string{"Other.pak", "Other.utoc", "Other.ucas"}}
	for _, n := range selected.Files {
		data.(fstest.MapFS)["payload/"+selected.ID+"/"+n] = &fstest.MapFile{Data: []byte("unrelated file")}
	}
	p, _ := installEdition(t, root, data, selected)
	assertPayload(t, p, data, editions[0].ID)
	for _, n := range selected.Files {
		if _, e := os.Stat(filepath.Join(p.Paks, n)); !os.IsNotExist(e) {
			t.Fatalf("non-runtime file installed: %s: %v", n, e)
		}
	}
}

func TestInvalidInstallationRecordsCannotModifyFiles(t *testing.T) {
	for _, damage := range []string{"invalid json", "missing manifest", "null manifest", "empty backup", "parent backup", "Windows stream backup", "unknown runtime", "duplicate runtime", "unknown backup file", "invalid hash"} {
		t.Run(damage, func(t *testing.T) {
			root, data := fixture(t)
			p, _ := installEdition(t, root, data, editions[0])
			snapshot := installedSnapshot(t, p)
			statePath := filepath.Join(root, stateName)
			var state installedState
			if e := json.Unmarshal(snapshot[statePath], &state); e != nil {
				t.Fatal(e)
			}
			state.Mode = ""
			state.Backup = "legacy"
			state.BackupFiles = []fileRecord{}
			switch damage {
			case "empty backup":
				state.Backup = ""
			case "parent backup":
				state.Backup = ".."
			case "Windows stream backup":
				state.Backup = "snapshot:stream"
			case "unknown runtime":
				state.Files[0].Name = "pakchunk9999-Windows_P.pak"
			case "duplicate runtime":
				state.Files[1] = state.Files[0]
			case "unknown backup file":
				state.BackupFiles = []fileRecord{{"../outside.pak", bytesHash([]byte("outside"))}}
			case "invalid hash":
				state.Files[0].SHA256 = "invalid"
			}
			b, e := json.Marshal(state)
			if e != nil {
				t.Fatal(e)
			}
			if damage == "missing manifest" || damage == "null manifest" {
				var fields map[string]json.RawMessage
				if e = json.Unmarshal(b, &fields); e != nil {
					t.Fatal(e)
				}
				if damage == "missing manifest" {
					delete(fields, "backup_files")
				} else {
					fields["backup_files"] = json.RawMessage("null")
				}
				b, e = json.Marshal(fields)
				if e != nil {
					t.Fatal(e)
				}
			}
			if damage == "invalid json" {
				b = []byte("{damaged record")
			}
			if e = os.WriteFile(statePath, b, 0644); e != nil {
				t.Fatal(e)
			}
			snapshot[statePath] = b
			if _, e = prepareInstall(data, editions[0], root); e == nil {
				t.Fatal("invalid record accepted for install")
			}
			if e = uninstall(root, nil); e == nil {
				t.Fatal("invalid record accepted for removal")
			}
			assertSnapshot(t, snapshot)
		})
	}
}

func TestInstallRejectsFileCreatedAfterPreflight(t *testing.T) {
	root, data := fixture(t)
	p, e := prepareInstall(data, editions[0], root)
	if e != nil {
		t.Fatal(e)
	}
	foreign := filepath.Join(p.Paks, runtimeNames[0])
	if e = os.WriteFile(foreign, []byte("third-party file"), 0644); e != nil {
		t.Fatal(e)
	}
	if _, e = install(p, nil); e == nil {
		t.Fatal("file changed after preflight was accepted")
	}
	assertSnapshot(t, map[string][]byte{foreign: []byte("third-party file")})
	if _, e = os.Stat(filepath.Join(root, stateName)); !os.IsNotExist(e) {
		t.Fatalf("failed install created a record: %v", e)
	}
}

func TestInstallCallbackCannotOverwriteNewForeignFile(t *testing.T) {
	root, data := fixture(t)
	p, e := prepareInstall(data, editions[0], root)
	if e != nil {
		t.Fatal(e)
	}
	foreign := filepath.Join(p.Paks, runtimeNames[0])
	_, e = install(p, func(s string) {
		if s == "Установка: "+runtimeNames[0] {
			if e := os.WriteFile(foreign, []byte("third-party file"), 0644); e != nil {
				t.Fatal(e)
			}
		}
	})
	if e == nil {
		t.Fatal("callback-created foreign file was accepted")
	}
	assertSnapshot(t, map[string][]byte{foreign: []byte("third-party file")})
}

func TestUninstallCallbackCannotDeleteChangedFile(t *testing.T) {
	root, data := fixture(t)
	p, _ := installEdition(t, root, data, editions[0])
	snapshot := installedSnapshot(t, p)
	changed := filepath.Join(p.Paks, runtimeNames[1])
	snapshot[changed] = []byte("user changes")
	e := uninstall(root, func(s string) {
		if s == "Удаление: "+runtimeNames[1] {
			if e := os.WriteFile(changed, snapshot[changed], 0644); e != nil {
				t.Fatal(e)
			}
		}
	})
	if e == nil {
		t.Fatal("callback changes were deleted")
	}
	assertSnapshot(t, snapshot)
}

func TestInstallRollbackPreservesConcurrentRecord(t *testing.T) {
	root, data := fixture(t)
	p, e := prepareInstall(data, editions[0], root)
	if e != nil {
		t.Fatal(e)
	}
	statePath := filepath.Join(root, stateName)
	foreign := []byte("record created by another process")
	_, e = install(p, func(s string) {
		if s == "Установка: "+runtimeNames[0] {
			if e := os.WriteFile(statePath, foreign, 0644); e != nil {
				t.Fatal(e)
			}
			if e := os.Mkdir(filepath.Join(p.Paks, runtimeNames[0]), 0755); e != nil {
				t.Fatal(e)
			}
			if e := os.WriteFile(filepath.Join(p.Paks, runtimeNames[0], "block"), []byte("keep"), 0644); e != nil {
				t.Fatal(e)
			}
		}
	})
	if e == nil {
		t.Fatal("obstructed install succeeded")
	}
	assertSnapshot(t, map[string][]byte{statePath: foreign, filepath.Join(p.Paks, runtimeNames[0], "block"): []byte("keep")})
}

func TestInstallChecksAlreadyWrittenFilesBeforeCommit(t *testing.T) {
	root, data := fixture(t)
	old, _ := installEdition(t, root, data, editions[1])
	snapshot := installedSnapshot(t, old)
	p, e := prepareInstall(data, editions[0], root)
	if e != nil {
		t.Fatal(e)
	}
	changed := filepath.Join(p.Paks, runtimeNames[0])
	snapshot[changed] = []byte("concurrent changes to a newly written file")
	_, e = install(p, func(s string) {
		if s == "Установка: "+runtimeNames[1] {
			if e := os.WriteFile(changed, snapshot[changed], 0644); e != nil {
				t.Fatal(e)
			}
		}
	})
	if e == nil {
		t.Fatal("changed first file was committed")
	}
	assertSnapshot(t, snapshot)
}

func failExclusiveWrite(t *testing.T, target string) error {
	t.Helper()
	injected := errors.New("injected partial write error")
	previous := writeExclusiveFile
	writeExclusiveFile = func(path string, data []byte) (bool, error) {
		if path != target {
			return createExclusiveFile(path, data)
		}
		partial := data
		if len(partial) > 1 {
			partial = partial[:len(partial)/2]
		}
		created, e := createExclusiveFile(path, partial)
		if e != nil {
			return created, e
		}
		return created, injected
	}
	t.Cleanup(func() { writeExclusiveFile = previous })
	return injected
}

func TestInstallRollsBackOwnPartialExclusiveWrites(t *testing.T) {
	for _, target := range []string{runtimeNames[1], stateName} {
		t.Run(target, func(t *testing.T) {
			root, data := fixture(t)
			old, _ := installEdition(t, root, data, editions[1])
			snapshot := installedSnapshot(t, old)
			p, e := prepareInstall(data, editions[0], root)
			if e != nil {
				t.Fatal(e)
			}
			path := filepath.Join(p.Paks, target)
			if target == stateName {
				path = filepath.Join(root, target)
			}
			injected := failExclusiveWrite(t, path)
			if _, e = install(p, nil); !errors.Is(e, injected) {
				t.Fatalf("write failure not reported: %v", e)
			}
			assertSnapshot(t, snapshot)
		})
	}
}

func createConcurrentFileInstead(t *testing.T, target string, contents []byte) {
	t.Helper()
	previous := writeExclusiveFile
	writeExclusiveFile = func(path string, data []byte) (bool, error) {
		if path != target {
			return createExclusiveFile(path, data)
		}
		if _, e := createExclusiveFile(path, contents); e != nil {
			t.Fatal(e)
		}
		return false, fs.ErrExist
	}
	t.Cleanup(func() { writeExclusiveFile = previous })
}

func TestStatePublishConflictNeverDeletesConcurrentRecord(t *testing.T) {
	root, data := fixture(t)
	p, _ := installEdition(t, root, data, editions[1])
	snapshot := installedSnapshot(t, p)
	statePath := filepath.Join(root, stateName)
	foreign := []byte("concurrent installation record")
	createConcurrentFileInstead(t, statePath, foreign)
	next, err := prepareInstall(data, editions[0], root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = install(next, nil); !errors.Is(err, fs.ErrExist) {
		t.Fatalf("state conflict not reported: %v", err)
	}
	snapshot[statePath] = foreign
	assertSnapshot(t, snapshot)
}

func TestHeldFileRecoveryNeverReplacesOccupiedDestination(t *testing.T) {
	root := t.TempDir()
	src, dst := filepath.Join(root, "held.pak"), filepath.Join(root, "destination.pak")
	if err := os.WriteFile(src, []byte("held original"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(dst, []byte("concurrent file"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := restoreHeldFile(src, dst); err == nil {
		t.Fatal("held original replaced an occupied destination")
	}
	assertSnapshot(t, map[string][]byte{src: []byte("held original"), dst: []byte("concurrent file")})
}
