; -----------------------------------------------------------------------------
; ZX0 decoder by Einar Saukas & Urusergi
; GBZ80 version by Tony Pavlov
; -----------------------------------------------------------------------------

        .title  "ZX0 Decompress"
        .module ZX0Decompress

        .area _HRAM

dzx0_temp::
        .ds 0x01

        .area _CODE

.macro EX_SP_HL
        push    de
        ld      a, l
        ld      d, h
        ldhl    sp, #2
        ld      e, (hl)
        ld      (hl+), a
        ld      a, (hl)
        ld      (hl), d
        ld      h, a
        ld      l, e
        pop     de
.endm

; -----------------------------------------------------------------------------
; Parameters for the SDCC UNZX0() function:
;   DE: source address (compressed data)
;   BC: destination address (decompressing)
; -----------------------------------------------------------------------------
_zx0_decompress::
        ld      h, d
        ld      l, e
        ld      d, b
        ld      e, c

; -----------------------------------------------------------------------------
; Parameters:
;   HL: source address (compressed data)
;   DE: destination address (decompressing)
; -----------------------------------------------------------------------------
dzx0_standard::
        ld      bc, #0xffff             ; preserve default offset 1
        push    bc
        inc     bc
        ld      a, #0x80
dzx0s_literals:
        call    dzx0s_elias             ; obtain length
        ldh     (dzx0_temp), a
        call    dzx0_ldir               ; copy literals
        ldh     a, (dzx0_temp)
        add     a, a                    ; copy from last offset or new offset?
        jr      c, dzx0s_new_offset
        call    dzx0s_elias             ; obtain length
dzx0s_copy:
        ldh     (dzx0_temp), a
        EX_SP_HL                        ; preserve source, restore offset
        push    hl                      ; preserve offset
        add     hl, de                  ; calculate destination - offset
        call    dzx0_ldir               ; copy from offset
        pop     hl                      ; restore offset
        EX_SP_HL                        ; preserve offset, restore source
        ldh     a, (dzx0_temp)
        add     a, a                    ; copy from literals or new offset?
        jr      nc, dzx0s_literals
dzx0s_new_offset:
        pop     bc                      ; discard last offset
        ld      c, #0xfe                ; prepare negative offset
        call    dzx0s_elias_loop        ; obtain offset MSB
        inc     c
        ret     z                       ; check end marker
        ld      b, c
        ld      c, (hl)                 ; obtain offset LSB
        inc     hl
        rr      b                       ; last offset bit becomes first length bit
        rr      c
        push    bc                      ; preserve new offset
        ld      bc, #1                  ; obtain length
        call    nc, dzx0s_elias_backtrack
        inc     bc
        jr      dzx0s_copy
dzx0s_elias:
        inc     c                       ; interlaced Elias gamma coding
dzx0s_elias_loop:
        add     a, a
        jr      nz, dzx0s_elias_skip
        ld      a, (hl+)                ; load another group of 8 bits
        rla
dzx0s_elias_skip:
        ret     c
dzx0s_elias_backtrack:
        add     a, a
        rl      c
        rl      b
        jr      dzx0s_elias_loop
dzx0_ldir:
	srl	b
	rr	c
        inc     b
        inc     c
        jr      c, 0$
        jr      1$
2$:
        ld      a, (hl+)
        ld      (de), a
        inc     de
0$:
        ld      a, (hl+)
        ld      (de), a
        inc     de
1$:
        dec     c
        jr      nz, 2$
        dec     b
        jr      nz, 2$
        ret
; -----------------------------------------------------------------------------
