        .include "global.s"

        .area   _CODE

        .globl ___sdcc_bcall
        .globl ___sdcc_bcall_abc

;
; trampoline to call banked functions
; used when legacy banking is enabled only
; Usage:
;   call ___sdcc_bcall
;   .dw  <function>
;   .dw  <function_bank>
;
___sdcc_bcall::
        ex (sp), hl
        ld c, (hl)
        inc hl
        ld b, (hl)
        inc hl
        ld a, (hl)
        inc hl
        inc  hl
        ex (sp), hl
        jp ___sdcc_bcall_abc
