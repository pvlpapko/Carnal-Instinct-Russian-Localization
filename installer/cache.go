package main

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

type cacheFile struct {
	Path string
	Info fs.FileInfo
}

type cachePlan struct {
	Root  string
	Files []cacheFile
	Bytes int64
}

// Refuse links and Windows junctions in every existing path component.
// A cache operation must never follow a redirected folder into saves or another game.
func cachePathInfo(path string) (fs.FileInfo, error) {
	abs, err := filepath.Abs(path)
	if err != nil {
		return nil, err
	}
	for p := abs; ; p = filepath.Dir(p) {
		st, e := os.Lstat(p)
		if e != nil {
			return nil, e
		}
		if st.Mode()&(os.ModeSymlink|os.ModeIrregular) != 0 {
			return nil, fmt.Errorf("очистка остановлена: ссылка или особый файл %s", p)
		}
		if filepath.Dir(p) == p {
			break
		}
	}
	resolved, err := filepath.EvalSymlinks(abs)
	if err != nil {
		return nil, err
	}
	if !strings.EqualFold(filepath.Clean(resolved), filepath.Clean(abs)) {
		return nil, fmt.Errorf("очистка остановлена: перенаправленная папка %s", abs)
	}
	return os.Lstat(abs)
}

func prepareCacheCleanup(input, localAppData string) (cachePlan, error) {
	root, _, err := locatePaks(input)
	plan := cachePlan{Root: root}
	if err != nil {
		return plan, err
	}
	bases := []string{root}
	if localAppData != "" {
		local, e := filepath.Abs(localAppData)
		if e != nil {
			return plan, e
		}
		bases = append(bases, filepath.Join(local, "Carnal_Instinct_UE5"))
	}
	seen := map[string]bool{}
	add := func(path string, st fs.FileInfo) error {
		if !st.Mode().IsRegular() {
			return fmt.Errorf("необычный файл кэша: %s", path)
		}
		if !seen[strings.ToLower(path)] {
			plan.Files = append(plan.Files, cacheFile{path, st})
			plan.Bytes += st.Size()
			seen[strings.ToLower(path)] = true
		}
		return nil
	}
	for _, base := range bases {
		// These are disposable Unreal caches, never the whole Saved directory.
		for _, rel := range []string{"DerivedDataCache", filepath.Join("Saved", "DerivedDataCache"), filepath.Join("Saved", "Shaders"), filepath.Join("Saved", "PipelineCaches")} {
			path := filepath.Join(base, rel)
			if _, e := os.Lstat(path); os.IsNotExist(e) {
				continue
			} else if e != nil {
				return plan, e
			}
			if _, e := cachePathInfo(path); e != nil {
				return plan, e
			}
			err = filepath.WalkDir(path, func(path string, entry fs.DirEntry, walkErr error) error {
				if walkErr != nil {
					return walkErr
				}
				st, e := cachePathInfo(path)
				if e != nil {
					return e
				}
				if st.IsDir() {
					return nil
				}
				return add(path, st)
			})
			if err != nil {
				return plan, err
			}
		}
		// UE5 can store driver/pipeline caches directly in Saved.
		saved := filepath.Join(base, "Saved")
		if _, e := os.Lstat(saved); os.IsNotExist(e) {
			continue
		} else if e != nil {
			return plan, e
		}
		if _, e := cachePathInfo(saved); e != nil {
			return plan, e
		}
		entries, e := os.ReadDir(saved)
		if e != nil {
			return plan, e
		}
		for _, entry := range entries {
			ext := strings.ToLower(filepath.Ext(entry.Name()))
			if ext != ".ushaderprecache" && ext != ".upipelinecache" {
				continue
			}
			path := filepath.Join(saved, entry.Name())
			st, e := cachePathInfo(path)
			if e != nil {
				return plan, e
			}
			if e = add(path, st); e != nil {
				return plan, e
			}
		}
	}
	return plan, nil
}

func clearGameCache(plan cachePlan) (int, error) {
	// Check the entire preview before deleting the first file.
	for _, f := range plan.Files {
		st, err := cachePathInfo(f.Path)
		if err != nil {
			return 0, err
		}
		if !st.Mode().IsRegular() || !os.SameFile(f.Info, st) || st.Size() != f.Info.Size() || !st.ModTime().Equal(f.Info.ModTime()) {
			return 0, fmt.Errorf("кэш изменился после проверки; закройте игру и повторите: %s", f.Path)
		}
	}
	for i, f := range plan.Files {
		if _, err := cachePathInfo(f.Path); err != nil {
			return i, err
		}
		if err := os.Remove(f.Path); err != nil {
			return i, err
		}
	}
	return len(plan.Files), nil
}
