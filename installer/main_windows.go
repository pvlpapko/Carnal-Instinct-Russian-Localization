//go:build windows

package main

import (
	"embed"
	"fmt"
	"os"
	"runtime"
	"strings"
	"syscall"
	"unsafe"
)

// Both newer NoSteam and Steam are resolved by payloadEdition in core.go.
// Keeping just the two real payload directories prevents edition drift.
//
//go:embed payload/*/* trusted_hashes.json LICENSE_RU.txt
var embedded embed.FS

const appTitle = "Carnal Instinct — Русификация: Don't Look"

const (
	wmCreate           = 0x0001
	wmDestroy          = 0x0002
	wmSize             = 0x0005
	wmPaint            = 0x000F
	wmClose            = 0x0010
	wmEraseBackground  = 0x0014
	wmGetMinMaxInfo    = 0x0024
	wmDrawItem         = 0x002B
	wmSetFont          = 0x0030
	wmSetIcon          = 0x0080
	wmCommand          = 0x0111
	wmCtlColorEdit     = 0x0133
	wmCtlColorButton   = 0x0135
	wmCtlColorStatic   = 0x0138
	wmDPIChanged       = 0x02E0
	wmAppEvent         = 0x8001
	wsOverlappedWindow = 0x00CF0000
	wsVisible          = 0x10000000
	wsChild            = 0x40000000
	wsClipChildren     = 0x02000000
	wsTabStop          = 0x00010000
	wsBorder           = 0x00800000
	wsVScroll          = 0x00200000
	wsGroup            = 0x00020000
	exControlParent    = 0x00010000
	bsOwnerDraw        = 0x0000000B
	esMultiline        = 0x0004
	esAutoVScroll      = 0x0040
	esAutoHScroll      = 0x0080
	esReadOnly         = 0x0800
	ssNoPrefix         = 0x0080
	dtWordBreak        = 0x0010
	dtSingleLine       = 0x0020
	dtVCenter          = 0x0004
	dtCenter           = 0x0001
	dtCalcRect         = 0x0400
	dtNoPrefix         = 0x0800
	odsSelected        = 0x0001
	odsDisabled        = 0x0004
	odsFocus           = 0x0010
	swShow             = 5
	imageIcon          = 1
	lrShared           = 0x8000
	lrDefaultSize      = 0x0040
	pbmSetMarquee      = 0x040A
	pbsMarquee         = 0x0008
	idAccept           = 101
	idEditionStart     = 110
	idPath             = 121
	idBrowse           = 122
	idRemove           = 123
	idCache            = 124
	idBack             = 130
	idNext             = 131
	idCancel           = 132
)

const (
	pageLicense = iota
	pageEdition
	pageFolder
	pageReview
	pageProgress
)

var (
	user32   = syscall.NewLazyDLL("user32.dll")
	kernel32 = syscall.NewLazyDLL("kernel32.dll")
	shell32  = syscall.NewLazyDLL("shell32.dll")
	ole32    = syscall.NewLazyDLL("ole32.dll")
	gdi32    = syscall.NewLazyDLL("gdi32.dll")
	dwmapi   = syscall.NewLazyDLL("dwmapi.dll")
	comctl32 = syscall.NewLazyDLL("comctl32.dll")

	pRegisterClassExW              = user32.NewProc("RegisterClassExW")
	pCreateWindowExW               = user32.NewProc("CreateWindowExW")
	pDefWindowProcW                = user32.NewProc("DefWindowProcW")
	pShowWindow                    = user32.NewProc("ShowWindow")
	pUpdateWindow                  = user32.NewProc("UpdateWindow")
	pDestroyWindow                 = user32.NewProc("DestroyWindow")
	pGetMessageW                   = user32.NewProc("GetMessageW")
	pTranslateMessage              = user32.NewProc("TranslateMessage")
	pDispatchMessageW              = user32.NewProc("DispatchMessageW")
	pIsDialogMessageW              = user32.NewProc("IsDialogMessageW")
	pPostQuitMessage               = user32.NewProc("PostQuitMessage")
	pSendMessageW                  = user32.NewProc("SendMessageW")
	pPostMessageW                  = user32.NewProc("PostMessageW")
	pGetWindowTextLengthW          = user32.NewProc("GetWindowTextLengthW")
	pGetWindowTextW                = user32.NewProc("GetWindowTextW")
	pSetWindowTextW                = user32.NewProc("SetWindowTextW")
	pLoadImageW                    = user32.NewProc("LoadImageW")
	pLoadCursorW                   = user32.NewProc("LoadCursorW")
	pGetClientRect                 = user32.NewProc("GetClientRect")
	pMoveWindow                    = user32.NewProc("MoveWindow")
	pEnableWindow                  = user32.NewProc("EnableWindow")
	pSetFocus                      = user32.NewProc("SetFocus")
	pGetFocus                      = user32.NewProc("GetFocus")
	pInvalidateRect                = user32.NewProc("InvalidateRect")
	pGetDC                         = user32.NewProc("GetDC")
	pReleaseDC                     = user32.NewProc("ReleaseDC")
	pFillRect                      = user32.NewProc("FillRect")
	pFrameRect                     = user32.NewProc("FrameRect")
	pDrawTextW                     = user32.NewProc("DrawTextW")
	pDrawFocusRect                 = user32.NewProc("DrawFocusRect")
	pBeginPaint                    = user32.NewProc("BeginPaint")
	pEndPaint                      = user32.NewProc("EndPaint")
	pAdjustWindowRectEx            = user32.NewProc("AdjustWindowRectEx")
	pAdjustWindowRectExForDpi      = user32.NewProc("AdjustWindowRectExForDpi")
	pGetDpiForWindow               = user32.NewProc("GetDpiForWindow")
	pGetDpiForSystem               = user32.NewProc("GetDpiForSystem")
	pSetProcessDpiAwarenessContext = user32.NewProc("SetProcessDpiAwarenessContext")
	pSetWindowPos                  = user32.NewProc("SetWindowPos")
	pGetSystemMetrics              = user32.NewProc("GetSystemMetrics")
	pMessageBoxW                   = user32.NewProc("MessageBoxW")
	pGetModuleHandleW              = kernel32.NewProc("GetModuleHandleW")
	pSHBrowseForFolderW            = shell32.NewProc("SHBrowseForFolderW")
	pSHGetPathFromIDListW          = shell32.NewProc("SHGetPathFromIDListW")
	pCoTaskMemFree                 = ole32.NewProc("CoTaskMemFree")
	pCoInitializeEx                = ole32.NewProc("CoInitializeEx")
	pCoUninitialize                = ole32.NewProc("CoUninitialize")
	pCreateSolidBrush              = gdi32.NewProc("CreateSolidBrush")
	pSetTextColor                  = gdi32.NewProc("SetTextColor")
	pSetBkColor                    = gdi32.NewProc("SetBkColor")
	pSetBkMode                     = gdi32.NewProc("SetBkMode")
	pCreateFontW                   = gdi32.NewProc("CreateFontW")
	pSelectObject                  = gdi32.NewProc("SelectObject")
	pDeleteObject                  = gdi32.NewProc("DeleteObject")
	pEllipse                       = gdi32.NewProc("Ellipse")
	pGetStockObject                = gdi32.NewProc("GetStockObject")
	pDwmSetWindowAttribute         = dwmapi.NewProc("DwmSetWindowAttribute")
	pInitCommonControlsEx          = comctl32.NewProc("InitCommonControlsEx")
)

type point struct{ X, Y int32 }
type rect struct{ Left, Top, Right, Bottom int32 }
type wndClassEx struct {
	Size, Style                        uint32
	WndProc                            uintptr
	ClassExtra, WindowExtra            int32
	Instance, Icon, Cursor, Background syscall.Handle
	MenuName, ClassName                *uint16
	SmallIcon                          syscall.Handle
}
type message struct {
	Window         syscall.Handle
	Message        uint32
	WParam, LParam uintptr
	Time           uint32
	Pt             point
	Private        uint32
}
type browseInfo struct {
	Owner              syscall.Handle
	Root               uintptr
	DisplayName, Title *uint16
	Flags              uint32
	Callback, Param    uintptr
	Image              int32
}
type drawItem struct {
	Type, ID, ItemID, Action, State uint32
	Window, DC                      syscall.Handle
	Rect                            rect
	Data                            uintptr
}
type paintStruct struct {
	DC              syscall.Handle
	Erase           int32
	Paint           rect
	Restore, Update int32
	Reserved        [32]byte
}
type minMaxInfo struct{ Reserved, MaxSize, MaxPosition, MinTrack, MaxTrack point }
type buttonInfo struct {
	Window           syscall.Handle
	Text, Note, Kind string
	EditionIndex     int
}
type uiEvent struct {
	Kind, Text, Operation string
	Plan                  *installPlan
	Removal               *removalReview
	Cache                 *cachePlan
	Success               bool
}
type removalReview struct{ Root, Paks, Edition string }

var (
	mainWindow                                                           syscall.Handle
	module                                                               syscall.Handle
	dpi                                                                  int32 = 96
	bodyFont, smallFont, boldFont, titleFont                             syscall.Handle
	backgroundBrush, panelBrush, borderBrush, accentBrush, selectedBrush syscall.Handle
	headerTitle, headerCredit, pageHeading, footerStep                   syscall.Handle
	backButton, nextButton, cancelButton                                 syscall.Handle
	pageControls                                                         []syscall.Handle
	buttonInfos                                                          = map[uint16]buttonInfo{}
	controls                                                             = map[string]syscall.Handle{}
	page                                                                 = pageLicense
	accepted                                                             bool
	selected                                                             = -1
	pathText                                                             string
	busy                                                                 bool
	resultReady                                                          bool
	resultSuccess                                                        bool
	progressText                                                         string
	currentPlan                                                          *installPlan
	currentRemoval                                                       *removalReview
	currentCache                                                         *cachePlan
	uiEvents                                                             = make(chan uiEvent, 128)
)

func utf16(s string) *uint16     { p, _ := syscall.UTF16PtrFromString(s); return p }
func color(r, g, b byte) uintptr { return uintptr(uint32(r) | uint32(g)<<8 | uint32(b)<<16) }
func dip(n int32) int32          { return (n*dpi + 48) / 96 }
func signed(n int32) uintptr     { return uintptr(n) }
func setText(window syscall.Handle, text string) {
	pSetWindowTextW.Call(uintptr(window), uintptr(unsafe.Pointer(utf16(text))))
}
func setFont(window, font syscall.Handle) {
	pSendMessageW.Call(uintptr(window), wmSetFont, uintptr(font), 1)
}
func enable(window syscall.Handle, enabled bool) {
	n := uintptr(0)
	if enabled {
		n = 1
	}
	pEnableWindow.Call(uintptr(window), n)
	pInvalidateRect.Call(uintptr(window), 0, 1)
}
func move(window syscall.Handle, x, y, w, h int32) {
	if w < 1 {
		w = 1
	}
	if h < 1 {
		h = 1
	}
	pMoveWindow.Call(uintptr(window), signed(x), signed(y), signed(w), signed(h), 1)
}
func windowText(window syscall.Handle) string {
	n, _, _ := pGetWindowTextLengthW.Call(uintptr(window))
	buf := make([]uint16, n+1)
	pGetWindowTextW.Call(uintptr(window), uintptr(unsafe.Pointer(&buf[0])), n+1)
	return syscall.UTF16ToString(buf)
}
func newWindow(class, text string, style uint32, parent syscall.Handle, id uint16) syscall.Handle {
	h, _, _ := pCreateWindowExW.Call(0, uintptr(unsafe.Pointer(utf16(class))), uintptr(unsafe.Pointer(utf16(text))), uintptr(style), 0, 0, 1, 1, uintptr(parent), uintptr(id), uintptr(module), 0)
	return syscall.Handle(h)
}
func newLabel(text string, font syscall.Handle) syscall.Handle {
	h := newWindow("STATIC", text, wsChild|wsVisible|ssNoPrefix, mainWindow, 0)
	setFont(h, font)
	return h
}
func pageLabel(name, text string, font syscall.Handle) syscall.Handle {
	h := newLabel(text, font)
	pageControls = append(pageControls, h)
	controls[name] = h
	return h
}
func pageEdit(name, text string, style uint32, id uint16) syscall.Handle {
	h := newWindow("EDIT", text, wsChild|wsVisible|wsBorder|wsTabStop|style, mainWindow, id)
	setFont(h, bodyFont)
	// A large limit is needed for the license and long result paths.
	pSendMessageW.Call(uintptr(h), 0x00C5, 1<<20, 0)
	// Provide clear inner margins without changing the text or wrapping behavior.
	pSendMessageW.Call(uintptr(h), 0x00D3, 3, uintptr(uint32(dip(9))|uint32(dip(9))<<16))
	pageControls = append(pageControls, h)
	controls[name] = h
	return h
}
func newButton(id uint16, text, note, kind string, index int, persistent bool) syscall.Handle {
	h := newWindow("BUTTON", text, wsChild|wsVisible|wsTabStop|bsOwnerDraw|wsGroup, mainWindow, id)
	setFont(h, bodyFont)
	buttonInfos[id] = buttonInfo{h, text, note, kind, index}
	if !persistent {
		pageControls = append(pageControls, h)
	}
	return h
}
func pageButton(name string, id uint16, text, note, kind string, index int) syscall.Handle {
	h := newButton(id, text, note, kind, index, false)
	controls[name] = h
	return h
}
func changeButton(id uint16, text string) {
	if b, ok := buttonInfos[id]; ok {
		b.Text = text
		buttonInfos[id] = b
		setText(b.Window, text)
		pInvalidateRect.Call(uintptr(b.Window), 0, 1)
	}
}
func makeFont(height, weight int32) syscall.Handle {
	h, _, _ := pCreateFontW.Call(signed(-dip(height)), 0, 0, 0, uintptr(weight), 0, 0, 0, 1, 0, 0, 5, 0, uintptr(unsafe.Pointer(utf16("Segoe UI"))))
	return syscall.Handle(h)
}
func recreateFonts() {
	old := []syscall.Handle{bodyFont, smallFont, boldFont, titleFont}
	bodyFont = makeFont(18, 400)
	smallFont = makeFont(16, 400)
	boldFont = makeFont(18, 600)
	titleFont = makeFont(27, 700)
	for _, h := range pageControls {
		setFont(h, bodyFont)
	}
	for _, b := range buttonInfos {
		setFont(b.Window, bodyFont)
	}
	setFont(headerTitle, titleFont)
	setFont(headerCredit, smallFont)
	setFont(pageHeading, boldFont)
	setFont(footerStep, smallFont)
	if h := controls["intro"]; h != 0 {
		setFont(h, bodyFont)
	}
	if h := controls["removeHelp"]; h != 0 {
		setFont(h, smallFont)
	}
	for _, f := range old {
		if f != 0 {
			pDeleteObject.Call(uintptr(f))
		}
	}
}
func textHeight(text string, width int32, font syscall.Handle) int32 {
	if width < 1 {
		width = 1
	}
	dc, _, _ := pGetDC.Call(uintptr(mainWindow))
	if dc == 0 {
		return dip(24)
	}
	old, _, _ := pSelectObject.Call(dc, uintptr(font))
	r := rect{Right: width}
	pDrawTextW.Call(dc, uintptr(unsafe.Pointer(utf16(text))), ^uintptr(0), uintptr(unsafe.Pointer(&r)), dtWordBreak|dtCalcRect|dtNoPrefix)
	pSelectObject.Call(dc, old)
	pReleaseDC.Call(uintptr(mainWindow), dc)
	if r.Bottom < dip(20) {
		return dip(20)
	}
	return r.Bottom + dip(3)
}
func textWidth(text string, font syscall.Handle) int32 {
	dc, _, _ := pGetDC.Call(uintptr(mainWindow))
	if dc == 0 {
		return dip(230)
	}
	old, _, _ := pSelectObject.Call(dc, uintptr(font))
	var r rect
	pDrawTextW.Call(dc, uintptr(unsafe.Pointer(utf16(text))), ^uintptr(0), uintptr(unsafe.Pointer(&r)), dtSingleLine|dtCalcRect|dtNoPrefix)
	pSelectObject.Call(dc, old)
	pReleaseDC.Call(uintptr(mainWindow), dc)
	return r.Right - r.Left
}
func buttonWidth(id uint16, minimum int32) int32 {
	if b, ok := buttonInfos[id]; ok {
		if measured := textWidth(b.Text, bodyFont) + dip(32); measured > minimum {
			return measured
		}
	}
	return minimum
}
func clearPage() {
	for _, h := range pageControls {
		pDestroyWindow.Call(uintptr(h))
		for id, b := range buttonInfos {
			if b.Window == h {
				delete(buttonInfos, id)
			}
		}
	}
	pageControls = nil
	controls = map[string]syscall.Handle{}
}
func payloadSourceLabel(e edition) string {
	if e.ID == steamPayloadEditionID {
		return "Steam"
	}
	if e.ID == "NoSteam_0.7.9.16313plus" {
		return "Steam (актуальный комплект)"
	}
	return payloadEdition(e)
}

func editionNote(index int) string {
	switch index {
	case 0:
		return "Русификатор 18.9. Исправлены размеры текста в настройках и журнале, уменьшен значок отслеживания. Исходная версия игры: 0.7.9.16321."
	case 1:
		return "Отдельный комплект для NoSteam 0.7.9.16232. Сохранены файлы перевода 18.6."
	default:
		return "Комплект Steam для новых сборок NoSteam. Совместимость с 0.7.9.16313/16315+ пока не проверена."
	}
}
func showPage(next int) {
	if page == pageFolder && controls["path"] != 0 {
		pathText = windowText(controls["path"])
	}
	clearPage()
	page = next
	switch page {
	case pageLicense:
		setText(pageHeading, "1. Лицензионное соглашение")
		pageLabel("intro", "Ознакомьтесь с условиями использования русификации.", bodyFont)
		license, _ := embedded.ReadFile("LICENSE_RU.txt")
		pageEdit("license", strings.ReplaceAll(strings.ReplaceAll(string(license), "\r\n", "\n"), "\n", "\r\n"), esMultiline|esAutoVScroll|esReadOnly|wsVScroll, 0)
		pageButton("accept", idAccept, "Я принимаю условия соглашения", "", "check", -1)
	case pageEdition:
		setText(pageHeading, "2. Версия игры")
		pageLabel("intro", "Выберите версию игры. Все комплекты встроены в установщик.", bodyFont)
		for i, e := range editions {
			pageButton(fmt.Sprintf("edition%d", i), uint16(idEditionStart+i), e.Label, editionNote(i), "edition", i)
		}
	case pageFolder:
		setText(pageHeading, "3. Папка игры")
		if selected >= 0 {
			pageLabel("intro", "Выбранная версия: "+editions[selected].Label, bodyFont)
		}
		pageLabel("pathLabel", "Папка Carnal Instinct:", bodyFont)
		pageEdit("path", pathText, esAutoHScroll, idPath)
		pageButton("browse", idBrowse, "Обзор…", "", "action", -1)
		pageLabel("help", "Укажите папку игры, папку Carnal_Instinct_UE5 или Content\\Paks. Перед установкой закройте игру.", bodyFont)
		pageButton("remove", idRemove, "Удалить русификацию", "", "action", -1)
		pageLabel("removeHelp", "Для удаления укажите папку с установленной русификацией.", smallFont)
		setFont(controls["removeHelp"], smallFont)
		pageButton("cache", idCache, "Очистить кэш игры", "", "action", -1)
		pageLabel("cacheHelp", "Отдельная очистка временных данных. Следующий запуск может быть дольше. Сохранения и настройки остаются.", smallFont)
	case pageReview:
		if currentCache != nil {
			setText(pageHeading, "4. Очистка кэша игры")
			pageLabel("intro", "Очистка выполняется отдельно от установки русификатора.", bodyFont)
			detail := fmt.Sprintf("Папка игры:\r\n%s\r\n\r\nНайдено файлов кэша: %d (%.1f МБ).\r\n\r\nКэш будет создан игрой заново. Первый запуск после очистки может занять больше времени.\r\n\r\nСохранения, настройки, журналы и другие моды сохраняются. Общий кэш видеодрайвера не очищается.\r\n\r\nЗакройте игру перед продолжением.", currentCache.Root, len(currentCache.Files), float64(currentCache.Bytes)/(1024*1024))
			if len(currentCache.Files) == 0 {
				detail += "\r\n\r\nПодходящий кэш не найден. Удалять нечего."
			}
			pageEdit("review", detail, esMultiline|esAutoVScroll|esReadOnly|wsVScroll, 0)
		} else if currentRemoval != nil {
			setText(pageHeading, "4. Проверка удаления")
			pageLabel("intro", "Проверьте папку и действие перед продолжением.", bodyFont)
			detail := "Действие: удалить установленную русификацию и её старые резервные копии.\r\n\r\nПапка игры:\r\n" + currentRemoval.Root + "\r\n\r\nТекущий комплект: " + currentRemoval.Edition + "\r\n\r\nФайлы:\r\n" + strings.Join(runtimeNames, "\r\n")

			detail += "\r\n\r\nЗакройте игру перед продолжением."
			pageEdit("review", detail, esMultiline|esAutoVScroll|esReadOnly|wsVScroll, 0)
		} else if currentPlan != nil {
			setText(pageHeading, "4. Проверка установки")
			pageLabel("intro", "Комплект и папка проверены. Проверьте выбранные параметры.", bodyFont)
			detail := "Версия игры: " + currentPlan.Edition.Label + "\r\n\r\nПапка игры:\r\n" + currentPlan.Root + "\r\n\r\nПапка установки:\r\n" + currentPlan.Paks + "\r\n\r\nИсточник файлов: " + payloadSourceLabel(currentPlan.Edition) + "\r\n\r\nПолный комплект:\r\n" + strings.Join(runtimeNames, "\r\n") + "\r\n\r\nПредыдущие файлы русификации будут заменены. Старые резервные копии русификатора будут удалены. Закройте игру перед установкой."
			pageEdit("review", detail, esMultiline|esAutoVScroll|esReadOnly|wsVScroll, 0)
		}
	case pageProgress:
		if busy {
			setText(pageHeading, "Выполнение операции")
		} else if resultSuccess {
			setText(pageHeading, "Готово")
		} else {
			setText(pageHeading, "Операция остановлена")
		}
		pageLabel("intro", func() string {
			if busy {
				return "Дождитесь завершения проверки файлов."
			}
			if resultSuccess {
				return "Операция выполнена. Подробности приведены ниже."
			}
			return "Проверьте сообщение и вернитесь к выбору папки при необходимости."
		}(), bodyFont)
		if busy {
			h := newWindow("msctls_progress32", "", wsChild|wsVisible|pbsMarquee, mainWindow, 0)
			pageControls = append(pageControls, h)
			controls["progressBar"] = h
			pSendMessageW.Call(uintptr(h), pbmSetMarquee, 1, 40)
		}
		pageEdit("progress", progressText, esMultiline|esAutoVScroll|esReadOnly|wsVScroll, 0)
	}
	updateFooter()
	layout()
	pInvalidateRect.Call(uintptr(mainWindow), 0, 1)
	focus := nextButton
	switch page {
	case pageLicense:
		focus = controls["license"]
	case pageEdition:
		focus = controls["edition0"]
	case pageFolder:
		focus = controls["path"]
	case pageReview:
		focus = nextButton
	}
	if !busy && focus != 0 {
		pSetFocus.Call(uintptr(focus))
	}
}
func updateFooter() {
	changeButton(idBack, "Назад")
	changeButton(idNext, "Далее")
	changeButton(idCancel, "Отмена")
	canNext := true
	switch page {
	case pageLicense:
		canNext = accepted
	case pageEdition:
		canNext = selected >= 0
	case pageReview:
		if currentCache != nil {
			changeButton(idNext, "Очистить кэш")
		} else if currentRemoval != nil {
			changeButton(idNext, "Удалить русификацию")
		} else {
			changeButton(idNext, "Установить")
		}
	case pageProgress:
		canNext = resultReady && !busy
		changeButton(idNext, "Готово")
		if resultReady {
			changeButton(idBack, "К папке игры")
			changeButton(idCancel, "Закрыть")
		}
	}
	enable(backButton, page > pageLicense && !busy)
	enable(nextButton, canNext && !busy)
	enable(cancelButton, !busy)
	step := "Don't Look"
	if page <= pageReview {
		step = fmt.Sprintf("Шаг %d из 4", page+1)
	}
	if page == pageProgress && busy {
		step = "Подождите…"
	}
	setText(footerStep, step)
}
func layout() {
	if mainWindow == 0 || headerTitle == 0 {
		return
	}
	var c rect
	pGetClientRect.Call(uintptr(mainWindow), uintptr(unsafe.Pointer(&c)))
	w, h := c.Right, c.Bottom
	margin := dip(28)
	contentW := w - 2*margin
	y := dip(22)
	th := textHeight("Русификация Carnal Instinct", contentW, titleFont)
	move(headerTitle, margin, y, contentW, th)
	y += th + dip(4)
	move(headerCredit, margin, y, contentW, dip(24))
	y += dip(36)
	ph := textHeight(windowText(pageHeading), contentW, boldFont)
	move(pageHeading, margin, y, contentW, ph)
	y += ph + dip(16)
	bodyTop := y
	bodyBottom := h - dip(102)
	bodyH := bodyBottom - bodyTop
	if bodyH < dip(100) {
		bodyH = dip(100)
	}
	introH := textHeight(windowText(controls["intro"]), contentW, bodyFont)
	move(controls["intro"], margin, y, contentW, introH)
	y += introH + dip(12)
	switch page {
	case pageLicense:
		acceptH := dip(46)
		editH := bodyBottom - y - acceptH - dip(12)
		move(controls["license"], margin, y, contentW, editH)
		move(controls["accept"], margin, bodyBottom-acceptH, contentW, acceptH)
	case pageEdition:
		for i, e := range editions {
			textW := contentW - dip(70)
			titleH := textHeight(e.Label, textW, boldFont)
			noteH := textHeight(editionNote(i), textW, smallFont)
			cardH := titleH + noteH + dip(25)
			if cardH < dip(88) {
				cardH = dip(88)
			}
			move(controls[fmt.Sprintf("edition%d", i)], margin, y, contentW, cardH)
			y += cardH + dip(10)
		}
	case pageFolder:
		labelH := textHeight(windowText(controls["pathLabel"]), contentW, bodyFont)
		move(controls["pathLabel"], margin, y, contentW, labelH)
		y += labelH + dip(8)
		browseW := dip(120)
		inputH := dip(40)
		move(controls["path"], margin, y, contentW-browseW-dip(12), inputH)
		move(controls["browse"], margin+contentW-browseW, y, browseW, inputH)
		y += inputH + dip(18)
		helpH := textHeight(windowText(controls["help"]), contentW, bodyFont)
		move(controls["help"], margin, y, contentW, helpH)
		y += helpH + dip(24)
		removeW := dip(285)
		if removeW > contentW {
			removeW = contentW
		}
		move(controls["remove"], margin, y, removeW, dip(46))
		y += dip(56)
		removeH := textHeight(windowText(controls["removeHelp"]), contentW, smallFont)
		move(controls["removeHelp"], margin, y, contentW, removeH)
		y += removeH + dip(16)
		move(controls["cache"], margin, y, removeW, dip(42))
		y += dip(50)
		cacheH := textHeight(windowText(controls["cacheHelp"]), contentW, smallFont)
		move(controls["cacheHelp"], margin, y, contentW, cacheH)
	case pageReview:
		move(controls["review"], margin, y, contentW, bodyBottom-y)
	case pageProgress:
		if controls["progressBar"] != 0 {
			move(controls["progressBar"], margin, y, contentW, dip(20))
			y += dip(34)
		}
		move(controls["progress"], margin, y, contentW, bodyBottom-y)
	}
	footerY := h - dip(68)
	buttonH := dip(42)
	cancelW := buttonWidth(idCancel, dip(114))
	nextW := buttonWidth(idNext, dip(220))
	backW := buttonWidth(idBack, dip(130))
	gap := dip(10)
	cx := w - margin - cancelW
	nx := cx - gap - nextW
	bx := nx - gap - backW
	move(backButton, bx, footerY, backW, buttonH)
	move(nextButton, nx, footerY, nextW, buttonH)
	move(cancelButton, cx, footerY, cancelW, buttonH)
	move(footerStep, margin, footerY+dip(9), bx-margin-dip(12), dip(25))
}
func drawText(dc syscall.Handle, text string, r rect, font syscall.Handle, fg uintptr, flags uintptr) {
	old, _, _ := pSelectObject.Call(uintptr(dc), uintptr(font))
	pSetTextColor.Call(uintptr(dc), fg)
	pSetBkMode.Call(uintptr(dc), 1)
	pDrawTextW.Call(uintptr(dc), uintptr(unsafe.Pointer(utf16(text))), ^uintptr(0), uintptr(unsafe.Pointer(&r)), flags|dtNoPrefix)
	pSelectObject.Call(uintptr(dc), old)
}
func drawButton(item *drawItem) {
	b, ok := buttonInfos[uint16(item.ID)]
	if !ok {
		return
	}
	r := item.Rect
	fill := panelBrush
	fg := color(242, 234, 222)
	border := borderBrush
	selectedCard := b.Kind == "edition" && selected == b.EditionIndex
	checked := b.Kind == "check" && accepted
	if selectedCard || checked {
		fill = selectedBrush
		border = accentBrush
	}
	if b.Kind == "primary" {
		fill = accentBrush
		fg = color(26, 20, 17)
	}
	if item.State&odsSelected != 0 {
		fill = selectedBrush
		if b.Kind == "primary" {
			fg = color(255, 244, 216)
		}
	}
	if item.State&odsDisabled != 0 {
		fill = panelBrush
		fg = color(135, 126, 126)
		border = borderBrush
	}
	if item.State&odsFocus != 0 {
		border = accentBrush
	}
	pFillRect.Call(uintptr(item.DC), uintptr(unsafe.Pointer(&r)), uintptr(fill))
	pFrameRect.Call(uintptr(item.DC), uintptr(unsafe.Pointer(&r)), uintptr(border))
	if b.Kind == "edition" {
		circle := rect{r.Left + dip(17), r.Top + dip(19), r.Left + dip(35), r.Top + dip(37)}
		brush := borderBrush
		if selectedCard {
			brush = accentBrush
		}
		old, _, _ := pSelectObject.Call(uintptr(item.DC), uintptr(brush))
		pen, _, _ := pGetStockObject.Call(8)
		oldPen, _, _ := pSelectObject.Call(uintptr(item.DC), pen)
		pEllipse.Call(uintptr(item.DC), signed(circle.Left), signed(circle.Top), signed(circle.Right), signed(circle.Bottom))
		if selectedCard {
			pSelectObject.Call(uintptr(item.DC), uintptr(backgroundBrush))
			inset := dip(5)
			pEllipse.Call(uintptr(item.DC), signed(circle.Left+inset), signed(circle.Top+inset), signed(circle.Right-inset), signed(circle.Bottom-inset))
		}
		pSelectObject.Call(uintptr(item.DC), oldPen)
		pSelectObject.Call(uintptr(item.DC), old)
		tr := rect{r.Left + dip(52), r.Top + dip(11), r.Right - dip(14), r.Bottom - dip(8)}
		ht := textHeight(b.Text, tr.Right-tr.Left, boldFont)
		titleRect := tr
		titleRect.Bottom = titleRect.Top + ht
		drawText(item.DC, b.Text, titleRect, boldFont, fg, dtWordBreak)
		tr.Top += ht + dip(3)
		drawText(item.DC, b.Note, tr, smallFont, color(210, 200, 196), dtWordBreak)
	} else if b.Kind == "check" {
		box := rect{r.Left + dip(15), r.Top + (r.Bottom-r.Top-dip(20))/2, r.Left + dip(35), r.Top + (r.Bottom-r.Top+dip(20))/2}
		pFrameRect.Call(uintptr(item.DC), uintptr(unsafe.Pointer(&box)), uintptr(border))
		if checked {
			drawText(item.DC, "✓", box, boldFont, color(241, 199, 99), dtCenter|dtVCenter|dtSingleLine)
		}
		tr := rect{r.Left + dip(48), r.Top + dip(5), r.Right - dip(12), r.Bottom - dip(5)}
		drawText(item.DC, b.Text, tr, bodyFont, fg, dtVCenter|dtSingleLine)
	} else {
		tr := rect{r.Left + dip(8), r.Top, r.Right - dip(8), r.Bottom}
		drawText(item.DC, b.Text, tr, bodyFont, fg, dtCenter|dtVCenter|dtSingleLine)
	}
	if item.State&odsFocus != 0 {
		fr := rect{r.Left + dip(4), r.Top + dip(4), r.Right - dip(4), r.Bottom - dip(4)}
		pDrawFocusRect.Call(uintptr(item.DC), uintptr(unsafe.Pointer(&fr)))
	}
}
func browseFolder() string {
	display := make([]uint16, 260)
	bi := browseInfo{Owner: mainWindow, DisplayName: &display[0], Title: utf16("Выберите папку Carnal Instinct или Carnal_Instinct_UE5"), Flags: 1 | 0x40 | 0x10, Image: -1}
	pidl, _, _ := pSHBrowseForFolderW.Call(uintptr(unsafe.Pointer(&bi)))
	if pidl == 0 {
		return ""
	}
	defer pCoTaskMemFree.Call(pidl)
	out := make([]uint16, 32768)
	ok, _, _ := pSHGetPathFromIDListW.Call(pidl, uintptr(unsafe.Pointer(&out[0])))
	if ok == 0 {
		return ""
	}
	return syscall.UTF16ToString(out)
}
func sendEvent(e uiEvent) { uiEvents <- e; pPostMessageW.Call(uintptr(mainWindow), wmAppEvent, 0, 0) }
func startWork(text string) {
	busy = true
	resultReady = false
	resultSuccess = false
	progressText = text
	showPage(pageProgress)
}
func prepareSelected() {
	if selected < 0 {
		return
	}
	pathText = windowText(controls["path"])
	input := pathText
	choice := editions[selected]
	currentRemoval = nil
	currentPlan = nil
	currentCache = nil
	startWork("Проверка встроенного комплекта и папки игры…")
	go func() {
		p, err := prepareInstall(embedded, choice, input)
		if err != nil {
			sendEvent(uiEvent{Kind: "complete", Text: "Установка не началась.\r\n\r\n" + err.Error()})
			return
		}
		sendEvent(uiEvent{Kind: "prepared", Plan: &p})
	}()
}
func prepareRemoval() {
	pathText = windowText(controls["path"])
	input := pathText
	currentPlan = nil
	currentRemoval = nil
	currentCache = nil
	startWork("Проверка записи установки…")
	go func() {
		root, paks, err := locatePaks(input)
		if err != nil {
			sendEvent(uiEvent{Kind: "complete", Text: "Удаление не началось.\r\n\r\n" + err.Error()})
			return
		}
		data, err := readState(root)
		if err != nil {
			sendEvent(uiEvent{Kind: "complete", Text: "Удаление не началось.\r\n\r\n" + err.Error()})
			return
		}
		if len(data) == 0 {
			sendEvent(uiEvent{Kind: "complete", Text: "Не найдена запись установки русификации.\r\n\r\nПроверьте выбранную папку. Файлы без записи установки автоматически не удаляются."})
			return
		}
		state, err := validateState(data)
		if err != nil {
			sendEvent(uiEvent{Kind: "complete", Text: err.Error()})
			return
		}
		label := state.Edition
		for _, e := range editions {
			if e.ID == state.Edition {
				label = e.Label
			}
		}
		sendEvent(uiEvent{Kind: "removalPrepared", Removal: &removalReview{root, paks, label}})
	}()
}
func prepareCache() {
	pathText = windowText(controls["path"])
	input := pathText
	currentPlan, currentRemoval, currentCache = nil, nil, nil
	startWork("Поиск кэша игры…")
	go func() {
		if err := requireGameClosed(); err != nil {
			sendEvent(uiEvent{Kind: "complete", Text: err.Error()})
			return
		}
		local, err := os.UserCacheDir()
		if err != nil {
			sendEvent(uiEvent{Kind: "complete", Text: err.Error()})
			return
		}
		p, err := prepareCacheCleanup(input, local)
		if err != nil {
			sendEvent(uiEvent{Kind: "complete", Text: "Очистка не началась.\r\n\r\n" + err.Error()})
			return
		}
		sendEvent(uiEvent{Kind: "cachePrepared", Cache: &p})
	}()
}

func commitOperation() {
	if currentCache != nil {
		p := *currentCache
		startWork("Очистка кэша игры…")
		go func() {
			if err := requireGameClosed(); err != nil {
				sendEvent(uiEvent{Kind: "complete", Text: err.Error()})
				return
			}
			n, err := clearGameCache(p)
			if err != nil {
				sendEvent(uiEvent{Kind: "complete", Text: fmt.Sprintf("Очистка остановлена. Удалено файлов: %d.\r\n\r\n%s", n, err)})
				return
			}
			text := fmt.Sprintf("Кэш игры очищен. Удалено файлов: %d.\r\n\r\nСохранения и настройки сохранены. Следующий запуск может быть дольше.", n)
			if n == 0 {
				text = "Подходящий кэш игры не найден. Файлы не удалялись."
			}
			sendEvent(uiEvent{Kind: "complete", Success: true, Text: text})
		}()
	} else if currentRemoval != nil {
		info := *currentRemoval
		startWork("Удаление русификации…")
		go func() {
			err := uninstall(info.Root, func(s string) { sendEvent(uiEvent{Kind: "progress", Text: s}) })
			if err != nil {
				sendEvent(uiEvent{Kind: "complete", Text: "Удаление остановлено.\r\n\r\n" + err.Error()})
				return
			}
			sendEvent(uiEvent{Kind: "complete", Success: true, Text: "Русификация и её старые резервные копии удалены.\r\n\r\nПапка игры:\r\n" + info.Root})
		}()
	} else if currentPlan != nil {
		p := *currentPlan
		startWork("Подготовка установки…")
		go func() {
			_, err := install(p, func(s string) { sendEvent(uiEvent{Kind: "progress", Text: s}) })
			if err != nil {
				text := "Установка остановлена.\r\n\r\n" + err.Error()

				sendEvent(uiEvent{Kind: "complete", Text: text})
				return
			}
			sendEvent(uiEvent{Kind: "complete", Success: true, Text: "Русификация установлена. Контрольные суммы всех трёх файлов проверены.\r\n\r\nКомплект: " + p.Edition.Label + "\r\n\r\nПапка игры:\r\n" + p.Root + "\r\n\r\nСтарые файлы заменены. Резервные копии не создаются."})
		}()
	}
}
func drainEvents() {
	for {
		select {
		case e := <-uiEvents:
			switch e.Kind {
			case "progress":
				progressText = e.Text
				if h := controls["progress"]; h != 0 {
					setText(h, e.Text)
				}
			case "prepared":
				busy = false
				currentPlan = e.Plan
				currentRemoval = nil
				currentCache = nil
				showPage(pageReview)
			case "removalPrepared":
				busy = false
				currentRemoval = e.Removal
				currentPlan = nil
				currentCache = nil
				showPage(pageReview)
			case "cachePrepared":
				busy = false
				currentCache = e.Cache
				currentPlan, currentRemoval = nil, nil
				showPage(pageReview)
			case "complete":
				busy = false
				resultReady = true
				resultSuccess = e.Success
				progressText = e.Text
				showPage(pageProgress)
			}
		default:
			return
		}
	}
}
func onCommand(id uint16) {
	if busy {
		return
	}
	switch {
	case id == idAccept:
		if page != pageLicense {
			return
		}
		accepted = !accepted
		pInvalidateRect.Call(uintptr(controls["accept"]), 0, 1)
		updateFooter()
	case id >= idEditionStart && int(id-idEditionStart) < len(editions):
		if page != pageEdition {
			return
		}
		selected = int(id - idEditionStart)
		for i := range editions {
			pInvalidateRect.Call(uintptr(controls[fmt.Sprintf("edition%d", i)]), 0, 1)
		}
		updateFooter()
	case id == idBrowse:
		if page != pageFolder {
			return
		}
		if chosen := browseFolder(); chosen != "" {
			pathText = chosen
			setText(controls["path"], chosen)
		}
	case id == idRemove:
		if page != pageFolder {
			return
		}
		prepareRemoval()
	case id == idCache:
		if page != pageFolder {
			return
		}
		prepareCache()
	case id == idBack:
		if page == pageProgress || page == pageReview {
			currentPlan = nil
			currentRemoval = nil
			currentCache = nil
			showPage(pageFolder)
		} else if page > pageLicense {
			showPage(page - 1)
		}
	case id == idNext:
		switch page {
		case pageLicense:
			if accepted {
				showPage(pageEdition)
			}
		case pageEdition:
			if selected >= 0 {
				showPage(pageFolder)
			}
		case pageFolder:
			prepareSelected()
		case pageReview:
			commitOperation()
		case pageProgress:
			if resultReady {
				pDestroyWindow.Call(uintptr(mainWindow))
			}
		}
	case id == idCancel:
		pDestroyWindow.Call(uintptr(mainWindow))
	}
}

// IsDialogMessage supplies Tab navigation; these keys keep owner-drawn buttons
// consistent with ordinary wizard controls without relying on dialog IDs.
func handleKeyboard(msg *message) bool {
	if msg.Message != 0x0100 {
		return false
	}
	focus, _, _ := pGetFocus.Call()
	if msg.WParam == 0x1B {
		if !busy {
			pDestroyWindow.Call(uintptr(mainWindow))
		}
		return true
	}
	if busy {
		return false
	}
	if msg.WParam == 0x0D {
		for id, b := range buttonInfos {
			if uintptr(b.Window) == focus {
				onCommand(id)
				return true
			}
		}
		if controls["path"] != 0 && uintptr(controls["path"]) == focus {
			onCommand(idNext)
			return true
		}
	}
	if page == pageEdition && (msg.WParam == 0x25 || msg.WParam == 0x26 || msg.WParam == 0x27 || msg.WParam == 0x28) {
		for _, b := range buttonInfos {
			if b.Kind == "edition" && uintptr(b.Window) == focus {
				step := 1
				if msg.WParam == 0x25 || msg.WParam == 0x26 {
					step = -1
				}
				index := (b.EditionIndex + step + len(editions)) % len(editions)
				onCommand(uint16(idEditionStart + index))
				pSetFocus.Call(uintptr(controls[fmt.Sprintf("edition%d", index)]))
				return true
			}
		}
	}
	return false
}

func adjustOuter(r *rect, targetDPI int32) {
	if pAdjustWindowRectExForDpi.Find() == nil {
		pAdjustWindowRectExForDpi.Call(uintptr(unsafe.Pointer(r)), wsOverlappedWindow, 0, exControlParent, uintptr(targetDPI))
	} else {
		pAdjustWindowRectEx.Call(uintptr(unsafe.Pointer(r)), wsOverlappedWindow, 0, exControlParent)
	}
}
func wndProc(window syscall.Handle, msg uint32, wParam, lParam uintptr) uintptr {
	switch msg {
	case wmCreate:
		mainWindow = window
		if pGetDpiForWindow.Find() == nil {
			n, _, _ := pGetDpiForWindow.Call(uintptr(window))
			if n > 0 {
				dpi = int32(n)
			}
		}
		backgroundBrush = syscall.Handle(mustBrush(color(22, 15, 19)))
		panelBrush = syscall.Handle(mustBrush(color(43, 33, 37)))
		borderBrush = syscall.Handle(mustBrush(color(109, 93, 96)))
		accentBrush = syscall.Handle(mustBrush(color(229, 187, 101)))
		selectedBrush = syscall.Handle(mustBrush(color(66, 47, 38)))
		headerTitle = newLabel("Русификация Carnal Instinct", 0)
		headerCredit = newLabel("Автор: Don't Look", 0)
		pageHeading = newLabel("", 0)
		footerStep = newLabel("", 0)
		backButton = newButton(idBack, "Назад", "", "action", -1, true)
		nextButton = newButton(idNext, "Далее", "", "primary", -1, true)
		cancelButton = newButton(idCancel, "Отмена", "", "action", -1, true)
		recreateFonts()
		showPage(pageLicense)
		dark := int32(1)
		if pDwmSetWindowAttribute.Find() == nil {
			pDwmSetWindowAttribute.Call(uintptr(window), 20, uintptr(unsafe.Pointer(&dark)), 4)
		}
		// A group icon resource supplies both sizes, without writing a temporary icon.
		big, _, _ := pLoadImageW.Call(uintptr(module), 1, imageIcon, uintptr(dip(32)), uintptr(dip(32)), lrShared)
		small, _, _ := pLoadImageW.Call(uintptr(module), 1, imageIcon, uintptr(dip(16)), uintptr(dip(16)), lrShared)
		if big != 0 {
			pSendMessageW.Call(uintptr(window), wmSetIcon, 1, big)
		}
		if small != 0 {
			pSendMessageW.Call(uintptr(window), wmSetIcon, 0, small)
		}
		return 0
	case wmSize:
		layout()
		return 0
	case wmGetMinMaxInfo:
		if lParam != 0 {
			m := (*minMaxInfo)(unsafe.Pointer(lParam))
			r := rect{Right: dip(740), Bottom: dip(700)}
			adjustOuter(&r, dpi)
			m.MinTrack = point{r.Right - r.Left, r.Bottom - r.Top}
		}
		return 0
	case wmDPIChanged:
		dpi = int32(uint16(wParam))
		recreateFonts()
		if lParam != 0 {
			r := (*rect)(unsafe.Pointer(lParam))
			pSetWindowPos.Call(uintptr(window), 0, signed(r.Left), signed(r.Top), signed(r.Right-r.Left), signed(r.Bottom-r.Top), 0x0014)
		}
		layout()
		pInvalidateRect.Call(uintptr(window), 0, 1)
		return 0
	case wmDrawItem:
		if lParam != 0 {
			drawButton((*drawItem)(unsafe.Pointer(lParam)))
			return 1
		}
	case wmCtlColorStatic, wmCtlColorEdit, wmCtlColorButton:
		pSetTextColor.Call(wParam, color(242, 234, 222))
		pSetBkMode.Call(wParam, 1)
		if msg == wmCtlColorEdit || syscall.Handle(lParam) == controls["license"] || syscall.Handle(lParam) == controls["review"] || syscall.Handle(lParam) == controls["progress"] {
			pSetBkColor.Call(wParam, color(43, 33, 37))
			return uintptr(panelBrush)
		}
		pSetBkColor.Call(wParam, color(22, 15, 19))
		return uintptr(backgroundBrush)
	case wmEraseBackground:
		return 1
	case wmPaint:
		var ps paintStruct
		pBeginPaint.Call(uintptr(window), uintptr(unsafe.Pointer(&ps)))
		var r rect
		pGetClientRect.Call(uintptr(window), uintptr(unsafe.Pointer(&r)))
		pFillRect.Call(uintptr(ps.DC), uintptr(unsafe.Pointer(&r)), uintptr(backgroundBrush))
		line := rect{dip(28), r.Bottom - dip(88), r.Right - dip(28), r.Bottom - dip(88) + 1}
		pFillRect.Call(uintptr(ps.DC), uintptr(unsafe.Pointer(&line)), uintptr(borderBrush))
		pEndPaint.Call(uintptr(window), uintptr(unsafe.Pointer(&ps)))
		return 0
	case wmCommand:
		if uint16(wParam>>16) == 0 {
			onCommand(uint16(wParam))
		}
		return 0
	case wmAppEvent:
		drainEvents()
		return 0
	case wmClose:
		if !busy {
			pDestroyWindow.Call(uintptr(window))
		}
		return 0
	case wmDestroy:
		pPostQuitMessage.Call(0)
		return 0
	}
	r, _, _ := pDefWindowProcW.Call(uintptr(window), uintptr(msg), wParam, lParam)
	return r
}
func mustBrush(c uintptr) uintptr { h, _, _ := pCreateSolidBrush.Call(c); return h }

func main() {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	// The embedded manifest selects PerMonitorV2; this also covers a source build
	// run before the resource step. E_ACCESSDENIED means a manifest already set it.
	if pSetProcessDpiAwarenessContext.Find() == nil {
		pSetProcessDpiAwarenessContext.Call(^uintptr(3))
	}
	if pGetDpiForSystem.Find() == nil {
		n, _, _ := pGetDpiForSystem.Call()
		if n > 0 {
			dpi = int32(n)
		}
	}
	pCoInitializeEx.Call(0, 2)
	defer pCoUninitialize.Call()
	ic := struct{ Size, Classes uint32 }{8, 0x20}
	pInitCommonControlsEx.Call(uintptr(unsafe.Pointer(&ic)))
	m, _, _ := pGetModuleHandleW.Call(0)
	module = syscall.Handle(m)
	cursor, _, _ := pLoadCursorW.Call(0, 32512)
	icon, _, _ := pLoadImageW.Call(m, 1, imageIcon, 0, 0, lrShared|lrDefaultSize)
	className := utf16("DontLook_CI_RU_Wizard_v3")
	wc := wndClassEx{Size: uint32(unsafe.Sizeof(wndClassEx{})), WndProc: syscall.NewCallback(wndProc), Instance: module, Cursor: syscall.Handle(cursor), Icon: syscall.Handle(icon), SmallIcon: syscall.Handle(icon), ClassName: className}
	registered, _, _ := pRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc)))
	if registered == 0 {
		pMessageBoxW.Call(0, uintptr(unsafe.Pointer(utf16("Не удалось создать окно установщика."))), uintptr(unsafe.Pointer(utf16(appTitle))), 0x10)
		return
	}
	r := rect{Right: dip(780), Bottom: dip(740)}
	adjustOuter(&r, dpi)
	width, height := r.Right-r.Left, r.Bottom-r.Top
	screenW, _, _ := pGetSystemMetrics.Call(0)
	screenH, _, _ := pGetSystemMetrics.Call(1)
	x, y := (int32(screenW)-width)/2, (int32(screenH)-height)/2
	if x < 0 {
		x = 0
	}
	if y < 0 {
		y = 0
	}
	h, _, _ := pCreateWindowExW.Call(exControlParent, uintptr(unsafe.Pointer(className)), uintptr(unsafe.Pointer(utf16(appTitle))), wsOverlappedWindow|wsClipChildren, signed(x), signed(y), signed(width), signed(height), 0, 0, m, 0)
	if h == 0 {
		pMessageBoxW.Call(0, uintptr(unsafe.Pointer(utf16("Не удалось открыть установщик."))), uintptr(unsafe.Pointer(utf16(appTitle))), 0x10)
		return
	}
	mainWindow = syscall.Handle(h)
	pShowWindow.Call(h, swShow)
	pUpdateWindow.Call(h)
	var msg message
	for {
		got, _, _ := pGetMessageW.Call(uintptr(unsafe.Pointer(&msg)), 0, 0, 0)
		if int32(got) <= 0 {
			break
		}
		if handleKeyboard(&msg) {
			continue
		}
		handled, _, _ := pIsDialogMessageW.Call(h, uintptr(unsafe.Pointer(&msg)))
		if handled == 0 {
			pTranslateMessage.Call(uintptr(unsafe.Pointer(&msg)))
			pDispatchMessageW.Call(uintptr(unsafe.Pointer(&msg)))
		}
	}
	for _, f := range []syscall.Handle{bodyFont, smallFont, boldFont, titleFont, backgroundBrush, panelBrush, borderBrush, accentBrush, selectedBrush} {
		if f != 0 {
			pDeleteObject.Call(uintptr(f))
		}
	}
}
