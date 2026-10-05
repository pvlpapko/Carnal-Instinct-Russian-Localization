package main

import (
 "bufio"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

// Switch actual diagnostic payloads using the real installer core, in a temp game.
func TestProbeReplacesStagesWithoutBackups(t *testing.T) {
 home := os.Getenv("CI_RU_PROBE_ROOT")
 if home == "" { t.Skip("real diagnostic payload root not provided") }
 data, err := os.ReadFile(filepath.Join(home, "PROBE_MANIFEST.json")); if err != nil { t.Fatal(err) }
 var manifest probeManifest; if err = json.Unmarshal(data, &manifest); err != nil { t.Fatal(err) }
 game := filepath.Join(t.TempDir(), "Carnal_Instinct_UE5")
 paks := filepath.Join(game, "Content", "Paks")
 if err = os.MkdirAll(paks, 0755); err != nil { t.Fatal(err) }
 foreign := filepath.Join(paks, "foreign_mod.pak")
 if err = os.WriteFile(foreign, []byte("keep"), 0644); err != nil { t.Fatal(err) }
 for _, number := range []int{0, 5, 9, 0} {
  input := bufio.NewReader(strings.NewReader(fmt.Sprintf("%d\n%s\n", number, game)))
  if err = runProbe(home, false, input); err != nil { t.Fatal(err) }
  for _, f := range manifest.Stages[number].Files {
   hash, e := fileHash(filepath.Join(paks, f.Name)); if e != nil || hash != f.SHA256 { t.Fatalf("stage %d: %s: %v", number, f.Name, e) }
  }
 }
 entries, err := os.ReadDir(game); if err != nil { t.Fatal(err) }
 for _, e := range entries { if strings.Contains(strings.ToLower(e.Name()), "backup") { t.Fatalf("backup created: %s", e.Name()) } }
 data, err = os.ReadFile(foreign); if err != nil || string(data) != "keep" { t.Fatal("foreign mod changed") }
 stateData, err := readState(game); if err != nil { t.Fatal(err) }
 state, err := validateState(stateData); if err != nil { t.Fatal(err) }
 if state.Edition != "Steam_current" || state.Mode != "replace" || state.Backup != "" { t.Fatal("invalid installed state") }
}
