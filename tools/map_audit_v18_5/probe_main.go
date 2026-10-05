// Standalone diagnostic launcher; build with the unchanged installer core.go.
package main

import (
 "bufio"
 "encoding/json"
 "fmt"
 "io/fs"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "strconv"
 "strings"
)

type probeStage struct {
 Folder string `json:"folder"`
 Label string `json:"label"`
 Files []fileRecord `json:"files"`
}
type probeManifest struct { Stages []probeStage `json:"stages"` }
type probeSource struct { home, payload fs.FS }
func (p probeSource) Open(name string) (fs.File, error) {
 if name == "trusted_hashes.json" { return p.home.Open(name) }
 prefix := "payload/Steam_current/"
 if !strings.HasPrefix(name, prefix) { return nil, fs.ErrNotExist }
 base := strings.TrimPrefix(name, prefix)
 if strings.Contains(base, "/") || !fs.ValidPath(base) { return nil, fs.ErrNotExist }
 return p.payload.Open(base)
}

func runProbe(home string, verifyOnly bool, input *bufio.Reader) error {
 data, err := os.ReadFile(filepath.Join(home, "PROBE_MANIFEST.json")); if err != nil { return err }
 var manifest probeManifest
 if err = json.Unmarshal(data, &manifest); err != nil { return err }
 if len(manifest.Stages) != 10 { return fmt.Errorf("неполный набор диагностики") }
 for _, stage := range manifest.Stages {
  if !fs.ValidPath(stage.Folder) || strings.Contains(stage.Folder, "/") || len(stage.Files) != 3 { return fmt.Errorf("неверный набор") }
  for _, f := range stage.Files {
   valid := false; for _, n := range runtimeNames { if f.Name == n { valid = true } }
   if !valid { return fmt.Errorf("неизвестный файл") }
   hash, e := fileHash(filepath.Join(home, "Payloads", stage.Folder, f.Name))
   if e != nil { return e }; if hash != f.SHA256 { return fmt.Errorf("контрольная сумма: %s/%s", stage.Folder, f.Name) }
  }
 }
 if verifyOnly { fmt.Println("PASS: 10 комплектов, 30 контрольных сумм; игра не изменена."); return nil }
 if runtime.GOOS == "windows" {
  out, e := exec.Command("tasklist.exe", "/FO", "CSV", "/NH").Output()
  if e != nil { return e }
  if strings.Contains(strings.ToLower(string(out)), "carnal_instinct_ue5") { return fmt.Errorf("закройте игру перед заменой перевода") }
 }
 fmt.Println("Don't Look — диагностика краша Steam 18.4. Только для Steam.")
 fmt.Println("Все наборы используют файлы 18.3/18.4. Новых правок 18.5 здесь нет.")
 for i, stage := range manifest.Stages { fmt.Printf("%d: %s\n", i, stage.Label) }
 fmt.Print("Номер набора (0–9): ")
 line, err := input.ReadString('\n'); if err != nil { return err }
 number, err := strconv.Atoi(strings.TrimSpace(line)); if err != nil || number < 0 || number >= len(manifest.Stages) { return fmt.Errorf("неверный номер") }
 fmt.Print("Папка установленной игры Steam: ")
 line, err = input.ReadString('\n'); if err != nil { return err }
 stage := manifest.Stages[number]
 source := probeSource{os.DirFS(home), os.DirFS(filepath.Join(home, "Payloads", stage.Folder))}
 plan, err := prepareInstall(source, editions[0], strings.TrimSpace(line)); if err != nil { return err }
 _, err = install(plan, func(s string) { fmt.Println(s) }); if err != nil { return err }
 fmt.Printf("Установлен набор %d: %s\nЗапустите игру и запишите, появляется ли главное меню.\n", number, stage.Label)
 return nil
}

func main() {
 home, err := os.Executable(); if err != nil { fmt.Println(err); os.Exit(1) }
 home = filepath.Dir(home)
 verify := len(os.Args) == 2 && os.Args[1] == "--verify"
 input := bufio.NewReader(os.Stdin)
 err = runProbe(home, verify, input)
 if err != nil { fmt.Println("Ошибка:", err) }
 if !verify { fmt.Print("Enter — закрыть окно: "); input.ReadString('\n') }
 if err != nil { os.Exit(1) }
}
