	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 15, 4	sdk_version 15, 4
	.globl	__Z9transformPKjPjm             ; -- Begin function _Z9transformPKjPjm
	.p2align	2
__Z9transformPKjPjm:                    ; @_Z9transformPKjPjm
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #32
	.cfi_def_cfa_offset 32
	str	x0, [sp, #24]
	str	x1, [sp, #16]
	str	x2, [sp, #8]
	str	xzr, [sp]
	b	LBB0_1
LBB0_1:                                 ; =>This Inner Loop Header: Depth=1
	ldr	x8, [sp]
	ldr	x9, [sp, #8]
	subs	x8, x8, x9
	b.hs	LBB0_4
	b	LBB0_2
LBB0_2:                                 ;   in Loop: Header=BB0_1 Depth=1
	ldr	x8, [sp, #24]
	ldr	x9, [sp]
	ldr	w8, [x8, x9, lsl #2]
	lsl	w8, w8, #1
	add	w8, w8, #1
	ldr	x9, [sp, #16]
	ldr	x10, [sp]
	str	w8, [x9, x10, lsl #2]
	b	LBB0_3
LBB0_3:                                 ;   in Loop: Header=BB0_1 Depth=1
	ldr	x8, [sp]
	add	x8, x8, #1
	str	x8, [sp]
	b	LBB0_1
LBB0_4:
	add	sp, sp, #32
	ret
	.cfi_endproc
                                        ; -- End function
.subsections_via_symbols
