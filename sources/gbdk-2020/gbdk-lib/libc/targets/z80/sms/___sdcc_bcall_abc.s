        .include "global.s"

        .area   _CODE

        .globl ___sdcc_bcall_abc

;
; trampoline to call banked functions with __z88dk_fastcall calling convention
; Usage:
;  ld   a, #<function_bank>
;  ld   bc, #<function>
;  call ___sdcc_bcall_abc
;
___sdcc_bcall_abc::
        push    hl
        ld      l, a
        ld      a, (#.MAP_FRAME1)
        ld      h, a
        ld      a, l
        ld      (#.MAP_FRAME1), a
        ex      (sp), hl
        inc     sp
        call    ___sdcc_bjump_abc
        dec     sp
        pop     bc
        ld      c, a
        ld      a, b
        ld      (#.MAP_FRAME1), a
        ld      a, c
        ret
;
___sdcc_bjump_abc:
        push    bc
        ret
