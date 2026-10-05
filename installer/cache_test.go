package main

import (
	"os"
	"path/filepath"
	"testing"
)

func cacheWrite(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("keep-or-cache"), 0644); err != nil {
		t.Fatal(err)
	}
}

func TestCacheCleanupPreservesSavesSettingsModsAndOtherGames(t *testing.T) {
	root, _ := fixture(t)
	local := t.TempDir()
	user := filepath.Join(local, "Carnal_Instinct_UE5")
	remove := []string{
		filepath.Join(root, "DerivedDataCache", "a", "cache.udd"),
		filepath.Join(user, "Saved", "PipelineCaches", "cache.upipelinecache"),
		filepath.Join(user, "Saved", "D3DDriverCache.ushaderprecache"),
	}
	keep := []string{
		filepath.Join(root, "Content", "Paks", "other-mod.pak"),
		filepath.Join(user, "Saved", "SaveGames", "player.sav"),
		filepath.Join(user, "Saved", "Config", "Windows", "Engine.ini"),
		filepath.Join(user, "Saved", "Logs", "game.log"),
		filepath.Join(user, "Saved", "unknown.bin"),
		filepath.Join(local, "OtherGame", "Saved", "D3DDriverCache.ushaderprecache"),
	}
	for _, path := range append(remove, keep...) {
		cacheWrite(t, path)
	}
	p, err := prepareCacheCleanup(root, local)
	if err != nil {
		t.Fatal(err)
	}
	if len(p.Files) != len(remove) {
		t.Fatalf("cache preview: got %d, want %d", len(p.Files), len(remove))
	}
	n, err := clearGameCache(p)
	if err != nil || n != len(remove) {
		t.Fatalf("clear: count=%d error=%v", n, err)
	}
	for _, path := range remove {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("cache remains: %s", path)
		}
	}
	for _, path := range keep {
		if _, err := os.Stat(path); err != nil {
			t.Fatalf("protected file removed: %s: %v", path, err)
		}
	}
}

func TestCacheCleanupAbsentIsNoOp(t *testing.T) {
	root, _ := fixture(t)
	p, err := prepareCacheCleanup(root, t.TempDir())
	if err != nil || len(p.Files) != 0 {
		t.Fatalf("missing cache: %v %v", p, err)
	}
	if n, err := clearGameCache(p); err != nil || n != 0 {
		t.Fatalf("no-op: %d %v", n, err)
	}
}

func TestCacheCleanupRefusesLinkedCacheWithoutChangingTarget(t *testing.T) {
	root, _ := fixture(t)
	outside := t.TempDir()
	path := filepath.Join(outside, "cache.udd")
	cacheWrite(t, path)
	if err := os.Symlink(outside, filepath.Join(root, "DerivedDataCache")); err != nil {
		t.Skip(err)
	}
	if _, err := prepareCacheCleanup(root, t.TempDir()); err == nil {
		t.Fatal("linked cache accepted")
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatal("link target changed", err)
	}
}

func TestCacheCleanupChecksAllFilesBeforeDeletingAfterPreview(t *testing.T) {
	root, _ := fixture(t)
	a := filepath.Join(root, "DerivedDataCache", "a", "first.udd")
	b := filepath.Join(root, "DerivedDataCache", "b", "last.udd")
	cacheWrite(t, a)
	cacheWrite(t, b)
	p, err := prepareCacheCleanup(root, t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := os.RemoveAll(filepath.Dir(b)); err != nil {
		t.Fatal(err)
	}
	outside := t.TempDir()
	target := filepath.Join(outside, "last.udd")
	cacheWrite(t, target)
	if err := os.Symlink(outside, filepath.Dir(b)); err != nil {
		t.Skip(err)
	}
	if _, err := clearGameCache(p); err == nil {
		t.Fatal("changed directory accepted")
	}
	for _, path := range []string{a, target} {
		if _, err := os.Stat(path); err != nil {
			t.Fatal("preflight did not protect file", path, err)
		}
	}
}

func TestRegularInstallKeepsShaderCache(t *testing.T) {
	root, data := fixture(t)
	path := filepath.Join(root, "Saved", "D3DDriverCache.ushaderprecache")
	cacheWrite(t, path)
	p, err := prepareInstall(data, editions[0], root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := install(p, nil); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatal("ordinary update removed cache", err)
	}
}
