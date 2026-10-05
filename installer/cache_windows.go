//go:build windows

package main

import (
	"fmt"
	"strings"
	"syscall"
	"unsafe"
)

// Do not clear a shader cache while the game can be writing it.
func requireGameClosed() error {
	type processEntry struct {
		Size, Usage, ProcessID      uint32
		Heap                        uintptr
		ModuleID, Threads, ParentID uint32
		Priority                    int32
		Flags                       uint32
		Exe                         [260]uint16
	}
	kernel := syscall.NewLazyDLL("kernel32.dll")
	handle, _, err := kernel.NewProc("CreateToolhelp32Snapshot").Call(2, 0)
	if handle == ^uintptr(0) {
		return fmt.Errorf("не удалось проверить, закрыта ли игра: %v", err)
	}
	defer syscall.CloseHandle(syscall.Handle(handle))
	entry := processEntry{Size: uint32(unsafe.Sizeof(processEntry{}))}
	first, next := kernel.NewProc("Process32FirstW"), kernel.NewProc("Process32NextW")
	ok, _, err := first.Call(handle, uintptr(unsafe.Pointer(&entry)))
	for ok != 0 {
		name := syscall.UTF16ToString(entry.Exe[:])
		if strings.EqualFold(name, "Carnal_Instinct_UE5.exe") || strings.EqualFold(name, "Carnal_Instinct_UE5-Win64-Shipping.exe") {
			return fmt.Errorf("закройте Carnal Instinct перед очисткой кэша")
		}
		ok, _, err = next.Call(handle, uintptr(unsafe.Pointer(&entry)))
	}
	if err != syscall.ERROR_NO_MORE_FILES {
		return fmt.Errorf("не удалось проверить процессы игры: %v", err)
	}
	return nil
}
