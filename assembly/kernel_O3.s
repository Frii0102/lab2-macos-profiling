	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 15, 4	sdk_version 15, 4
	.globl	__Z9transformPKjPjm             ; -- Begin function _Z9transformPKjPjm
	.p2align	2
__Z9transformPKjPjm:                    ; @_Z9transformPKjPjm
	.cfi_startproc
; %bb.0:
	cbz	x2, LBB0_8
; %bb.1:
	mov	x8, #0                          ; =0x0
	cmp	x2, #16
	b.lo	LBB0_6
; %bb.2:
	sub	x9, x1, x0
	cmp	x9, #63
	b.ls	LBB0_6
; %bb.3:
	and	x8, x2, #0xfffffffffffffff0
	add	x9, x1, #32
	add	x10, x0, #32
	mov	x11, x8
LBB0_4:                                 ; =>This Inner Loop Header: Depth=1
	ldp	q0, q1, [x10, #-32]
	ldp	q2, q3, [x10], #64
	add.4s	v0, v0, v0
	add.4s	v1, v1, v1
	add.4s	v2, v2, v2
	add.4s	v3, v3, v3
	orr.4s	v0, #1
	orr.4s	v1, #1
	orr.4s	v2, #1
	orr.4s	v3, #1
	stp	q0, q1, [x9, #-32]
	stp	q2, q3, [x9], #64
	subs	x11, x11, #16
	b.ne	LBB0_4
; %bb.5:
	cmp	x8, x2
	b.eq	LBB0_8
LBB0_6:
	sub	x9, x2, x8
	lsl	x10, x8, #2
	add	x8, x1, x10
	add	x10, x0, x10
	mov	w11, #1                         ; =0x1
LBB0_7:                                 ; =>This Inner Loop Header: Depth=1
	ldr	w12, [x10], #4
	orr	w12, w11, w12, lsl #1
	str	w12, [x8], #4
	subs	x9, x9, #1
	b.ne	LBB0_7
LBB0_8:
	ret
	.cfi_endproc
                                        ; -- End function
.subsections_via_symbols
