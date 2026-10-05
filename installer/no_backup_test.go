package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInstallReplacesWithoutCreatingBackup(t *testing.T) {
	root, data := fixture(t)
	for _, selected := range []edition{editions[0], editions[1]} {
		p, err := prepareInstall(data, selected, root)
		if err != nil {
			t.Fatal(err)
		}
		backup, err := install(p, nil)
		if err != nil {
			t.Fatal(err)
		}
		if backup != "" {
			t.Fatalf("unexpected persistent backup: %s", backup)
		}
		if _, err := os.Lstat(filepath.Join(root, "CI_RU_Backup")); !os.IsNotExist(err) {
			t.Fatalf("backup directory exists: %v", err)
		}
		for _, f := range p.Files {
			got, err := fileHash(filepath.Join(p.Paks, f.Name))
			if err != nil || got != f.SHA256 {
				t.Fatalf("incorrect installed file %s: %v", f.Name, err)
			}
		}
	}
	if err := uninstall(root, nil); err != nil {
		t.Fatal(err)
	}
	for _, name := range runtimeNames {
		if _, err := os.Lstat(filepath.Join(root, "Content", "Paks", name)); !os.IsNotExist(err) {
			t.Fatalf("uninstall restored an old translation: %s", name)
		}
	}
}

func TestInstallRemovesOldLocalizationBackupButKeepsForeignFiles(t *testing.T) {
	root, data := fixture(t)
	old := filepath.Join(root, "CI_RU_Backup", "Previous", "20261004_120000_1234")
	if err := os.MkdirAll(old, 0755); err != nil {
		t.Fatal(err)
	}
	for _, name := range runtimeNames {
		b, err := data.Open("payload/" + editions[0].ID + "/" + name)
		if err != nil {
			t.Fatal(err)
		}
		b.Close()
		if err := os.WriteFile(filepath.Join(old, name), []byte(editions[0].ID+"/"+name), 0644); err != nil {
			t.Fatal(err)
		}
	}
	foreign := filepath.Join(old, "other-mod.pak")
	if err := os.WriteFile(foreign, []byte("keep"), 0644); err != nil {
		t.Fatal(err)
	}
	p, err := prepareInstall(data, editions[1], root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := install(p, nil); err != nil {
		t.Fatal(err)
	}
	for _, name := range runtimeNames {
		if _, err := os.Lstat(filepath.Join(old, name)); !os.IsNotExist(err) {
			t.Fatalf("old backup remains: %s", name)
		}
	}
	if b, err := os.ReadFile(foreign); err != nil || string(b) != "keep" {
		t.Fatal("foreign backup deleted", err)
	}
}

func TestInstallCleansOldPowerShellBackupBesideGameFolder(t *testing.T) {
	root, data := fixture(t)
	folder := filepath.Join(filepath.Dir(root), "RU_DontLook_Backup", "20261002_120000")
	if err := os.MkdirAll(folder, 0755); err != nil {
		t.Fatal(err)
	}
	for _, n := range append(append([]string{}, runtimeNames...), "RussianTranslation_P.pak") {
		if err := os.WriteFile(filepath.Join(folder, n), []byte("old localization"), 0644); err != nil {
			t.Fatal(err)
		}
	}
	p, err := prepareInstall(data, editions[0], root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := install(p, nil); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Lstat(folder); !os.IsNotExist(err) {
		t.Fatal("old PowerShell backup remains", err)
	}
}

func TestBackupCleanupDoesNotFollowSymlinks(t *testing.T) {
	root, data := fixture(t)
	outside := t.TempDir()
	file := filepath.Join(outside, runtimeNames[0])
	if err := os.WriteFile(file, []byte(editions[0].ID+"/"+runtimeNames[0]), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "CI_RU_Backup"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "CI_RU_Backup", "Previous")); err != nil {
		t.Skip(err)
	}
	p, err := prepareInstall(data, editions[0], root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := install(p, nil); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(file); err != nil {
		t.Fatal("symlink target changed", err)
	}
}
