        .include "global.s"

        .area   _CODE

        .globl ___sdcc_bcall_ehl

;
; default trampoline to call banked functions
; Usage:
;  ld   e, #<function_bank>
;  ld   hl, #<function>
;  call ___sdcc_bcall_ehl
;
___sdcc_bcall_ehl::
        ld      a, (#.MAP_FRAME1)
        push    af
        inc     sp
        ld      a, e
        ld      (#.MAP_FRAME1), a
        CALL_HL
        dec     sp
        pop     bc
        ld      c, a
        ld      a, b
        ld      (#.MAP_FRAME1), a
        ld      a, c
        ret
