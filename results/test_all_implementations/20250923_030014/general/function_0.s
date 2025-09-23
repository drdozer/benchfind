# Function: _ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$12scale_values17hcdb7e64963056f75E
# Lines: 21-884
# Implementation context: Unknown
# Extracted: 2025-09-23T03:00:33+01:00

_ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$12scale_values17hcdb7e64963056f75E:
	.cfi_startproc
	vmovsd	.LCPI0_1(%rip), %xmm1
	movq	%rdx, %rcx
	movl	$2, %edx
	vucomisd	%xmm0, %xmm1
	jbe	.LBB0_2
	vmovsd	.LCPI0_0(%rip), %xmm1
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.4(%rip), %rax
	testq	%rcx, %rcx
	jne	.LBB0_11
	jmp	.LBB0_24
.LBB0_2:
	vmovsd	.LCPI0_0(%rip), %xmm2
	vucomisd	%xmm0, %xmm2
	jbe	.LBB0_4
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.3(%rip), %rax
	testq	%rcx, %rcx
	jne	.LBB0_11
	jmp	.LBB0_24
.LBB0_4:
	vmovsd	.LCPI0_3(%rip), %xmm1
	vucomisd	%xmm0, %xmm1
	jbe	.LBB0_6
	vmovsd	.LCPI0_2(%rip), %xmm1
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.2(%rip), %rax
	movl	$3, %edx
	testq	%rcx, %rcx
	jne	.LBB0_11
	jmp	.LBB0_24
.LBB0_6:
	vmovsd	.LCPI0_4(%rip), %xmm1
	xorl	%edx, %edx
	vucomisd	%xmm0, %xmm1
	seta	%al
	ja	.LBB0_7
	vmovsd	.LCPI0_6(%rip), %xmm1
	jmp	.LBB0_9
.LBB0_7:
	vmovsd	.LCPI0_5(%rip), %xmm1
.LBB0_9:
	movb	%al, %dl
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.1(%rip), %rdi
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.0(%rip), %rax
	cmovaq	%rdi, %rax
	incq	%rdx
	testq	%rcx, %rcx
	je	.LBB0_24
.LBB0_11:
	leaq	(,%rcx,8), %r9
	movq	%rsi, %r10
	addq	$-8, %r9
	cmpq	$24, %r9
	jb	.LBB0_22
	movq	%r9, %rdi
	movabsq	$4611686018427387888, %r8
	shrq	$3, %rdi
	incq	%rdi
	cmpq	$120, %r9
	jae	.LBB0_17
	xorl	%r9d, %r9d
	jmp	.LBB0_14
.LBB0_17:
	movq	%rdi, %r9
	vbroadcastsd	%xmm1, %ymm0
	xorl	%r10d, %r10d
	andq	%r8, %r9
	.p2align	4
.LBB0_18:
	vmulpd	(%rsi,%r10,8), %ymm0, %ymm2
	vmulpd	32(%rsi,%r10,8), %ymm0, %ymm3
	vmulpd	64(%rsi,%r10,8), %ymm0, %ymm4
	vmulpd	96(%rsi,%r10,8), %ymm0, %ymm5
	vmovupd	%ymm2, (%rsi,%r10,8)
	vmovupd	%ymm3, 32(%rsi,%r10,8)
	vmovupd	%ymm4, 64(%rsi,%r10,8)
	vmovupd	%ymm5, 96(%rsi,%r10,8)
	addq	$16, %r10
	cmpq	%r10, %r9
	jne	.LBB0_18
	cmpq	%r9, %rdi
	je	.LBB0_24
	testb	$12, %dil
	je	.LBB0_21
.LBB0_14:
	addq	$12, %r8
	vbroadcastsd	%xmm1, %ymm0
	andq	%rdi, %r8
	leaq	(%rsi,%r8,8), %r10
	.p2align	4
.LBB0_15:
	vmulpd	(%rsi,%r9,8), %ymm0, %ymm2
	vmovupd	%ymm2, (%rsi,%r9,8)
	addq	$4, %r9
	cmpq	%r9, %r8
	jne	.LBB0_15
	cmpq	%r8, %rdi
	jne	.LBB0_22
	jmp	.LBB0_24
.LBB0_21:
	leaq	(%rsi,%r9,8), %r10
.LBB0_22:
	leaq	(%rsi,%rcx,8), %rcx
	.p2align	4
.LBB0_23:
	vmulsd	(%r10), %xmm1, %xmm0
	vmovsd	%xmm0, (%r10)
	addq	$8, %r10
	cmpq	%rcx, %r10
	jne	.LBB0_23
.LBB0_24:
	vzeroupper
	retq
.Lfunc_end0:
	.size	_ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$12scale_values17hcdb7e64963056f75E, .Lfunc_end0-_ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$12scale_values17hcdb7e64963056f75E
	.cfi_endproc

	.section	".text._ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$18scale_for_machines17h726d22e5b1921ae3E","ax",@progbits
	.p2align	4
	.type	_ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$18scale_for_machines17h726d22e5b1921ae3E,@function
_ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$18scale_for_machines17h726d22e5b1921ae3E:
	.cfi_startproc
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.3(%rip), %rax
	movl	$2, %edx
	retq
.Lfunc_end1:
	.size	_ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$18scale_for_machines17h726d22e5b1921ae3E, .Lfunc_end1-_ZN100_$LT$criterion..measurement..DurationFormatter$u20$as$u20$criterion..measurement..ValueFormatter$GT$18scale_for_machines17h726d22e5b1921ae3E
	.cfi_endproc

	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0
.LCPI2_0:
	.quad	1
	.quad	8
	.quad	0
	.quad	0
	.section	".text.unlikely._ZN103_$LT$std..sys..thread_local..abort_on_dtor_unwind..DtorUnwindGuard$u20$as$u20$core..ops..drop..Drop$GT$4drop17h3b8adf3e46d539f1E","ax",@progbits
	.p2align	4
	.type	_ZN103_$LT$std..sys..thread_local..abort_on_dtor_unwind..DtorUnwindGuard$u20$as$u20$core..ops..drop..Drop$GT$4drop17h3b8adf3e46d539f1E,@function
_ZN103_$LT$std..sys..thread_local..abort_on_dtor_unwind..DtorUnwindGuard$u20$as$u20$core..ops..drop..Drop$GT$4drop17h3b8adf3e46d539f1E:
	.cfi_startproc
	subq	$56, %rsp
	.cfi_def_cfa_offset 64
	vmovaps	.LCPI2_0(%rip), %ymm0
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.6(%rip), %rax
	leaq	7(%rsp), %rdi
	leaq	8(%rsp), %rsi
	movq	%rax, 8(%rsp)
	vmovups	%ymm0, 16(%rsp)
	vzeroupper
	callq	_ZN3std2io5Write9write_fmt17h61911005e056ac2bE
	movq	%rax, %rdi
	callq	_ZN4core3ptr81drop_in_place$LT$core..result..Result$LT$$LP$$RP$$C$std..io..error..Error$GT$$GT$17h8c98f9ea88f410a9E
	callq	*_ZN3std7process5abort17h5350951a259d9996E@GOTPCREL(%rip)
.Lfunc_end2:
	.size	_ZN103_$LT$std..sys..thread_local..abort_on_dtor_unwind..DtorUnwindGuard$u20$as$u20$core..ops..drop..Drop$GT$4drop17h3b8adf3e46d539f1E, .Lfunc_end2-_ZN103_$LT$std..sys..thread_local..abort_on_dtor_unwind..DtorUnwindGuard$u20$as$u20$core..ops..drop..Drop$GT$4drop17h3b8adf3e46d539f1E
	.cfi_endproc

	.section	".text._ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17h002d3713932352bbE","ax",@progbits
	.p2align	4
	.type	_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17h002d3713932352bbE,@function
_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17h002d3713932352bbE:
	.cfi_startproc
	movq	(%rdi), %rcx
	cmpq	$3, %rcx
	je	.LBB3_26
	movq	112(%rdi), %rax
	testq	%rax, %rax
	je	.LBB3_7
	movq	128(%rdi), %rdx
	movzbl	136(%rdi), %esi
	movq	120(%rdi), %r8
	decq	%rdx
	.p2align	4
.LBB3_3:
	cmpq	%r8, %rax
	je	.LBB3_6
	leaq	1(%rax), %r9
	leaq	2(%rdx), %r10
	incq	%rdx
	movq	%r9, 112(%rdi)
	cmpb	%sil, (%rax)
	movq	%r9, %rax
	movq	%r10, 128(%rdi)
	jne	.LBB3_3
	movl	$1, %eax
	retq
.LBB3_6:
	movq	$0, 112(%rdi)
.LBB3_7:
	cmpl	$2, %ecx
	je	.LBB3_25
	movzbl	88(%rdi), %eax
	testb	$1, %cl
	je	.LBB3_13
	movq	80(%rdi), %rdx
	movq	8(%rdi), %rsi
	movq	16(%rdi), %rcx
	decq	%rdx
	.p2align	4
.LBB3_10:
	cmpq	%rsi, %rcx
	je	.LBB3_13
	leaq	1(%rsi), %r8
	leaq	2(%rdx), %r9
	incq	%rdx
	movq	%r8, 8(%rdi)
	cmpb	%al, 24(%rdi,%rsi)
	movq	%r8, %rsi
	movq	%r9, 80(%rdi)
	jne	.LBB3_10
	jmp	.LBB3_12
.LBB3_13:
	movq	64(%rdi), %rcx
	testq	%rcx, %rcx
	je	.LBB3_20
	movq	72(%rdi), %r8
	cmpq	%r8, %rcx
	je	.LBB3_20
	movq	80(%rdi), %rdx
	.p2align	4
.LBB3_16:
	movzwl	(%rcx), %esi
	cmpb	%sil, %al
	je	.LBB3_33
	movl	%esi, %r9d
	shrl	$8, %r9d
	cmpb	%r9b, %al
	je	.LBB3_34
	addq	$2, %rcx
	addq	$2, %rdx
	cmpq	%r8, %rcx
	jne	.LBB3_16
	movq	%rdx, 80(%rdi)
	movq	$2, 8(%rdi)
	movq	$2, 16(%rdi)
	movw	%si, 24(%rdi)
	movq	%rcx, 64(%rdi)
.LBB3_20:
	movq	$0, (%rdi)
	cmpl	$1, 32(%rdi)
	jne	.LBB3_24
	movq	80(%rdi), %rdx
	movq	40(%rdi), %rsi
	movq	48(%rdi), %rcx
	decq	%rdx
	.p2align	4
.LBB3_22:
	cmpq	%rsi, %rcx
	je	.LBB3_24
	leaq	1(%rsi), %r8
	leaq	2(%rdx), %r9
	incq	%rdx
	movq	%r8, 40(%rdi)
	cmpb	%al, 56(%rdi,%rsi)
	movq	%r8, %rsi
	movq	%r9, 80(%rdi)
	jne	.LBB3_22
.LBB3_12:
	addq	104(%rdi), %rdx
	movl	$1, %eax
	retq
.LBB3_24:
	movq	$0, 32(%rdi)
.LBB3_25:
	movq	$3, (%rdi)
.LBB3_26:
	movq	144(%rdi), %r8
	testq	%r8, %r8
	je	.LBB3_31
	movq	160(%rdi), %r9
	movzbl	168(%rdi), %edx
	movq	152(%rdi), %rsi
	movl	$1, %ecx
	xorl	%eax, %eax
	subq	%r9, %rcx
	incq	%r9
	.p2align	4
.LBB3_28:
	cmpq	%rsi, %r8
	je	.LBB3_32
	leaq	1(%r8), %r10
	decq	%rcx
	movq	%r10, 144(%rdi)
	cmpb	%dl, (%r8)
	movq	%r9, 160(%rdi)
	leaq	1(%r9), %r9
	movq	%r10, %r8
	jne	.LBB3_28
	movq	200(%rdi), %rdx
	addq	%rdx, %rdx
	addq	184(%rdi), %rdx
	subq	%rcx, %rdx
	movl	$1, %eax
	retq
.LBB3_31:
	xorl	%eax, %eax
.LBB3_32:
	retq
.LBB3_33:
	leaq	1(%rdx), %r8
	movl	$1, %eax
	jmp	.LBB3_35
.LBB3_34:
	leaq	1(%rdx), %r9
	addq	$2, %rdx
	movl	$2, %eax
	movq	%rdx, %r8
	movq	%r9, %rdx
.LBB3_35:
	addq	$2, %rcx
	movq	%r8, 80(%rdi)
	movq	$1, (%rdi)
	movq	$2, 16(%rdi)
	movw	%si, 24(%rdi)
	movq	%rcx, 64(%rdi)
	movq	%rax, 8(%rdi)
	addq	104(%rdi), %rdx
	movl	$1, %eax
	retq
.Lfunc_end3:
	.size	_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17h002d3713932352bbE, .Lfunc_end3-_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17h002d3713932352bbE
	.cfi_endproc

	.section	".text._ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17hda0adee345b53c50E","ax",@progbits
	.p2align	4
	.type	_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17hda0adee345b53c50E,@function
_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17hda0adee345b53c50E:
	.cfi_startproc
	movq	(%rdi), %rax
	cmpq	$3, %rax
	je	.LBB4_32
	movq	112(%rdi), %rcx
	testq	%rcx, %rcx
	je	.LBB4_7
	movq	128(%rdi), %rdx
	movzbl	136(%rdi), %esi
	movq	120(%rdi), %r8
	decq	%rdx
	.p2align	4
.LBB4_3:
	cmpq	%r8, %rcx
	je	.LBB4_6
	leaq	1(%rcx), %r9
	leaq	2(%rdx), %r10
	incq	%rdx
	movq	%r9, 112(%rdi)
	cmpb	%sil, (%rcx)
	movq	%r9, %rcx
	movq	%r10, 128(%rdi)
	jne	.LBB4_3
	movl	$1, %eax
	retq
.LBB4_6:
	movq	$0, 112(%rdi)
.LBB4_7:
	cmpl	$2, %eax
	je	.LBB4_31
	movzbl	88(%rdi), %esi
	testb	$1, %al
	je	.LBB4_13
	movq	80(%rdi), %rdx
	movq	8(%rdi), %rcx
	movq	16(%rdi), %rax
	decq	%rdx
	.p2align	4
.LBB4_10:
	cmpq	%rcx, %rax
	je	.LBB4_13
	leaq	1(%rcx), %r8
	leaq	2(%rdx), %r9
	incq	%rdx
	movq	%r8, 8(%rdi)
	cmpb	%sil, 24(%rdi,%rcx)
	movq	%r8, %rcx
	movq	%r9, 80(%rdi)
	jne	.LBB4_10
	jmp	.LBB4_12
.LBB4_13:
	movq	64(%rdi), %rax
	testq	%rax, %rax
	je	.LBB4_26
	movq	72(%rdi), %r9
	cmpq	%r9, %rax
	je	.LBB4_26
	movq	80(%rdi), %rdx
	xorl	%ecx, %ecx
.LBB4_16:
	movq	(%rax,%rcx), %r8
	cmpb	%r8b, %sil
	je	.LBB4_39
	movl	%r8d, %r10d
	shrl	$8, %r10d
	cmpb	%r10b, %sil
	je	.LBB4_40
	movl	%r8d, %r10d
	shrl	$16, %r10d
	cmpb	%r10b, %sil
	je	.LBB4_41
	movl	%r8d, %r10d
	shrl	$24, %r10d
	cmpb	%r10b, %sil
	je	.LBB4_42
	movq	%r8, %r10
	shrq	$32, %r10
	cmpb	%r10b, %sil
	je	.LBB4_43
	movq	%r8, %r10
	shrq	$40, %r10
	cmpb	%r10b, %sil
	je	.LBB4_44
	movq	%r8, %r10
	shrq	$48, %r10
	cmpb	%r10b, %sil
	je	.LBB4_45
	movq	%r8, %r10
	shrq	$56, %r10
	cmpb	%r10b, %sil
	je	.LBB4_46
	leaq	8(%rax,%rcx), %r10
	addq	$8, %rcx
	cmpq	%r9, %r10
	jne	.LBB4_16
	addq	%rcx, %rdx
	addq	%rcx, %rax
	movq	%rdx, 80(%rdi)
	movq	$8, 8(%rdi)
	movq	$8, 16(%rdi)
	movq	%r8, 24(%rdi)
	movq	%rax, 64(%rdi)
.LBB4_26:
	movq	$0, (%rdi)
	cmpl	$1, 32(%rdi)
	jne	.LBB4_30
	movq	80(%rdi), %rdx
	movq	40(%rdi), %rcx
	movq	48(%rdi), %rax
	decq	%rdx
	.p2align	4
.LBB4_28:
	cmpq	%rcx, %rax
	je	.LBB4_30
	leaq	1(%rcx), %r8
	leaq	2(%rdx), %r9
	incq	%rdx
	movq	%r8, 40(%rdi)
	cmpb	%sil, 56(%rdi,%rcx)
	movq	%r8, %rcx
	movq	%r9, 80(%rdi)
	jne	.LBB4_28
.LBB4_12:
	addq	104(%rdi), %rdx
	movl	$1, %eax
	retq
.LBB4_30:
	movq	$0, 32(%rdi)
.LBB4_31:
	movq	$3, (%rdi)
.LBB4_32:
	movq	144(%rdi), %r8
	testq	%r8, %r8
	je	.LBB4_37
	movq	160(%rdi), %r9
	movzbl	168(%rdi), %edx
	movq	152(%rdi), %rsi
	movl	$1, %ecx
	xorl	%eax, %eax
	subq	%r9, %rcx
	incq	%r9
	.p2align	4
.LBB4_34:
	cmpq	%rsi, %r8
	je	.LBB4_38
	leaq	1(%r8), %r10
	decq	%rcx
	movq	%r10, 144(%rdi)
	cmpb	%dl, (%r8)
	movq	%r9, 160(%rdi)
	leaq	1(%r9), %r9
	movq	%r10, %r8
	jne	.LBB4_34
	movq	200(%rdi), %rdx
	shlq	$3, %rdx
	addq	184(%rdi), %rdx
	subq	%rcx, %rdx
	movl	$1, %eax
	retq
.LBB4_37:
	xorl	%eax, %eax
.LBB4_38:
	retq
.LBB4_39:
	leaq	1(%rdx,%rcx), %rsi
	addq	%rcx, %rdx
	movl	$1, %r9d
	jmp	.LBB4_47
.LBB4_40:
	leaq	2(%rdx,%rcx), %rsi
	leaq	1(%rdx,%rcx), %rdx
	movl	$2, %r9d
	jmp	.LBB4_47
.LBB4_41:
	leaq	3(%rdx,%rcx), %rsi
	leaq	2(%rdx,%rcx), %rdx
	movl	$3, %r9d
	jmp	.LBB4_47
.LBB4_42:
	leaq	4(%rdx,%rcx), %rsi
	leaq	3(%rdx,%rcx), %rdx
	movl	$4, %r9d
	jmp	.LBB4_47
.LBB4_43:
	leaq	5(%rdx,%rcx), %rsi
	leaq	4(%rdx,%rcx), %rdx
	movl	$5, %r9d
	jmp	.LBB4_47
.LBB4_44:
	leaq	6(%rdx,%rcx), %rsi
	leaq	5(%rdx,%rcx), %rdx
	movl	$6, %r9d
	jmp	.LBB4_47
.LBB4_45:
	leaq	7(%rdx,%rcx), %rsi
	leaq	6(%rdx,%rcx), %rdx
	movl	$7, %r9d
	jmp	.LBB4_47
.LBB4_46:
	leaq	8(%rdx,%rcx), %rsi
	leaq	7(%rdx,%rcx), %rdx
	movl	$8, %r9d
.LBB4_47:
	leaq	8(%rax,%rcx), %rax
	movq	%rsi, 80(%rdi)
	movq	$1, (%rdi)
	movq	$8, 16(%rdi)
	movq	%r8, 24(%rdi)
	movq	%rax, 64(%rdi)
	movq	%r9, 8(%rdi)
	addq	104(%rdi), %rdx
	movl	$1, %eax
	retq
.Lfunc_end4:
	.size	_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17hda0adee345b53c50E, .Lfunc_end4-_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17hda0adee345b53c50E
	.cfi_endproc

	.section	".text._ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17heacb210ad204d297E","ax",@progbits
	.p2align	4
	.type	_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17heacb210ad204d297E,@function
_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17heacb210ad204d297E:
	.cfi_startproc
	movq	(%rdi), %rcx
	cmpq	$3, %rcx
	je	.LBB5_28
	movq	112(%rdi), %rax
	testq	%rax, %rax
	je	.LBB5_7
	movq	128(%rdi), %rdx
	movzbl	136(%rdi), %esi
	movq	120(%rdi), %r8
	decq	%rdx
	.p2align	4
.LBB5_3:
	cmpq	%r8, %rax
	je	.LBB5_6
	leaq	1(%rax), %r9
	leaq	2(%rdx), %r10
	incq	%rdx
	movq	%r9, 112(%rdi)
	cmpb	%sil, (%rax)
	movq	%r9, %rax
	movq	%r10, 128(%rdi)
	jne	.LBB5_3
	movl	$1, %eax
	retq
.LBB5_6:
	movq	$0, 112(%rdi)
.LBB5_7:
	cmpl	$2, %ecx
	je	.LBB5_27
	movzbl	88(%rdi), %eax
	testb	$1, %cl
	je	.LBB5_13
	movq	80(%rdi), %rdx
	movq	8(%rdi), %rsi
	movq	16(%rdi), %rcx
	decq	%rdx
	.p2align	4
.LBB5_10:
	cmpq	%rsi, %rcx
	je	.LBB5_13
	leaq	1(%rsi), %r8
	leaq	2(%rdx), %r9
	incq	%rdx
	movq	%r8, 8(%rdi)
	cmpb	%al, 24(%rdi,%rsi)
	movq	%r8, %rsi
	movq	%r9, 80(%rdi)
	jne	.LBB5_10
	jmp	.LBB5_12
.LBB5_13:
	movq	64(%rdi), %rcx
	testq	%rcx, %rcx
	je	.LBB5_22
	movq	72(%rdi), %r9
	cmpq	%r9, %rcx
	je	.LBB5_22
	movq	80(%rdi), %rdx
	xorl	%esi, %esi
	.p2align	4
.LBB5_16:
	movl	(%rcx,%rsi), %r8d
	cmpb	%r8b, %al
	je	.LBB5_35
	movl	%r8d, %r10d
	shrl	$8, %r10d
	cmpb	%r10b, %al
	je	.LBB5_36
	movl	%r8d, %r10d
	shrl	$16, %r10d
	cmpb	%r10b, %al
	je	.LBB5_37
	movl	%r8d, %r10d
	shrl	$24, %r10d
	cmpb	%r10b, %al
	je	.LBB5_38
	leaq	4(%rcx,%rsi), %r10
	addq	$4, %rsi
	cmpq	%r9, %r10
	jne	.LBB5_16
	addq	%rsi, %rdx
	addq	%rsi, %rcx
	movq	%rdx, 80(%rdi)
	movq	$4, 8(%rdi)
	movq	$4, 16(%rdi)
	movl	%r8d, 24(%rdi)
	movq	%rcx, 64(%rdi)
.LBB5_22:
	movq	$0, (%rdi)
	cmpl	$1, 32(%rdi)
	jne	.LBB5_26
	movq	80(%rdi), %rdx
	movq	40(%rdi), %rsi
	movq	48(%rdi), %rcx
	decq	%rdx
	.p2align	4
.LBB5_24:
	cmpq	%rsi, %rcx
	je	.LBB5_26
	leaq	1(%rsi), %r8
	leaq	2(%rdx), %r9
	incq	%rdx
	movq	%r8, 40(%rdi)
	cmpb	%al, 56(%rdi,%rsi)
	movq	%r8, %rsi
	movq	%r9, 80(%rdi)
	jne	.LBB5_24
.LBB5_12:
	addq	104(%rdi), %rdx
	movl	$1, %eax
	retq
.LBB5_26:
	movq	$0, 32(%rdi)
.LBB5_27:
	movq	$3, (%rdi)
.LBB5_28:
	movq	144(%rdi), %r8
	testq	%r8, %r8
	je	.LBB5_33
	movq	160(%rdi), %r9
	movzbl	168(%rdi), %edx
	movq	152(%rdi), %rsi
	movl	$1, %ecx
	xorl	%eax, %eax
	subq	%r9, %rcx
	incq	%r9
	.p2align	4
.LBB5_30:
	cmpq	%rsi, %r8
	je	.LBB5_34
	leaq	1(%r8), %r10
	decq	%rcx
	movq	%r10, 144(%rdi)
	cmpb	%dl, (%r8)
	movq	%r9, 160(%rdi)
	leaq	1(%r9), %r9
	movq	%r10, %r8
	jne	.LBB5_30
	movq	200(%rdi), %rdx
	shlq	$2, %rdx
	addq	184(%rdi), %rdx
	subq	%rcx, %rdx
	movl	$1, %eax
	retq
.LBB5_33:
	xorl	%eax, %eax
.LBB5_34:
	retq
.LBB5_35:
	leaq	1(%rdx,%rsi), %rax
	addq	%rsi, %rdx
	movl	$1, %r9d
	jmp	.LBB5_39
.LBB5_36:
	leaq	2(%rdx,%rsi), %rax
	leaq	1(%rdx,%rsi), %rdx
	movl	$2, %r9d
	jmp	.LBB5_39
.LBB5_37:
	leaq	3(%rdx,%rsi), %rax
	leaq	2(%rdx,%rsi), %rdx
	movl	$3, %r9d
	jmp	.LBB5_39
.LBB5_38:
	leaq	4(%rdx,%rsi), %rax
	leaq	3(%rdx,%rsi), %rdx
	movl	$4, %r9d
.LBB5_39:
	leaq	4(%rcx,%rsi), %rcx
	movq	%rax, 80(%rdi)
	movq	$1, (%rdi)
	movq	$4, 16(%rdi)
	movl	%r8d, 24(%rdi)
	movq	%rcx, 64(%rdi)
	movq	%r9, 8(%rdi)
	addq	104(%rdi), %rdx
	movl	$1, %eax
	retq
.Lfunc_end5:
	.size	_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17heacb210ad204d297E, .Lfunc_end5-_ZN106_$LT$core..iter..adapters..chain..Chain$LT$A$C$B$GT$$u20$as$u20$core..iter..traits..iterator..Iterator$GT$4next17heacb210ad204d297E
	.cfi_endproc

	.section	".text._ZN106_$LT$criterion..routine..Function$LT$M$C$F$C$T$GT$$u20$as$u20$criterion..routine..Routine$LT$M$C$T$GT$$GT$5bench17h11cc4cbfde1703beE","ax",@progbits
	.p2align	4
	.type	_ZN106_$LT$criterion..routine..Function$LT$M$C$F$C$T$GT$$u20$as$u20$criterion..routine..Routine$LT$M$C$T$GT$$GT$5bench17h11cc4cbfde1703beE,@function
_ZN106_$LT$criterion..routine..Function$LT$M$C$F$C$T$GT$$u20$as$u20$criterion..routine..Routine$LT$M$C$T$GT$$GT$5bench17h11cc4cbfde1703beE:
.Lfunc_begin0:
	.cfi_startproc
	.cfi_personality 155, DW.ref.rust_eh_personality
	.cfi_lsda 27, .Lexception0
	pushq	%rbp
	.cfi_def_cfa_offset 16
	pushq	%r15
	.cfi_def_cfa_offset 24
	pushq	%r14
	.cfi_def_cfa_offset 32
	pushq	%r13
	.cfi_def_cfa_offset 40
	pushq	%r12
	.cfi_def_cfa_offset 48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	subq	$88, %rsp
	.cfi_def_cfa_offset 144
	.cfi_offset %rbx, -56
	.cfi_offset %r12, -48
	.cfi_offset %r13, -40
	.cfi_offset %r14, -32
	.cfi_offset %r15, -24
	.cfi_offset %rbp, -16
	movq	%r8, %r15
	movb	$0, 80(%rsp)
	movq	$0, 32(%rsp)
	movl	$0, 40(%rsp)
	movq	%rdx, 64(%rsp)
	movq	$0, 48(%rsp)
	movl	$0, 56(%rsp)
	testq	%r8, %r8
	je	.LBB6_1
	movq	%r9, %r13
	movq	%rcx, %rbp
	movq	%rdi, 8(%rsp)
	leaq	(,%r15,8), %rbx
	callq	*_RNvCsIV6ETmvI9x_7___rustc35___rust_no_alloc_shim_is_unstable_v2@GOTPCREL(%rip)
	movl	$8, %esi
	movq	%rbx, %rdi
	movq	%rbx, (%rsp)
	callq	*_RNvCsIV6ETmvI9x_7___rustc12___rust_alloc@GOTPCREL(%rip)
	testq	%rax, %rax
	je	.LBB6_14
	movq	__floattidf@GOTPCREL(%rip), %rbx
	movq	%rax, %r14
	xorl	%r12d, %r12d
	.p2align	4
.LBB6_5:
	movq	(%rbp,%r12,8), %rax
	movq	144(%rsp), %rcx
	movq	%r13, 16(%rsp)
	movq	%rax, 72(%rsp)
	movq	%rcx, 24(%rsp)
	movq	24(%rsp), %rdx
	movq	16(%rsp), %rsi
.Ltmp0:
	leaq	32(%rsp), %rdi
	callq	_ZN9criterion7bencher16Bencher$LT$M$GT$4iter17h7c6230d1284f8cd0E
.Ltmp1:
	cmpb	$0, 80(%rsp)
	je	.LBB6_7
	movb	$0, 80(%rsp)
	movl	$1000000000, %edx
	mulxq	32(%rsp), %rdi, %rsi
	movl	40(%rsp), %eax
	addq	%rax, %rdi
	adcq	$0, %rsi
	callq	*%rbx
	vmovsd	%xmm0, (%r14,%r12,8)
	incq	%r12
	cmpq	%r12, %r15
	jne	.LBB6_5
	movq	8(%rsp), %rdi
	jmp	.LBB6_2
.LBB6_1:
	movl	$8, %r14d
.LBB6_2:
	movq	%r15, (%rdi)
	movq	%r14, 8(%rdi)
	movq	%r15, 16(%rdi)
	movq	%rdi, %rax
	addq	$88, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%r12
	.cfi_def_cfa_offset 40
	popq	%r13
	.cfi_def_cfa_offset 32
	popq	%r14
	.cfi_def_cfa_offset 24
	popq	%r15
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	retq
.LBB6_7:
	.cfi_def_cfa_offset 144
.Ltmp3:
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.7(%rip), %rdi
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.9(%rip), %rdx
	movl	$61, %esi
	callq	*_ZN3std9panicking11begin_panic17h39556960b5edaff7E@GOTPCREL(%rip)
.Ltmp4:
	ud2
.LBB6_14:
	movq	(%rsp), %rsi
	leaq	.Lanon.7523289b42aa3fbf5f32607ea11c5738.152(%rip), %rdx
	movl	$8, %edi
	callq	*_ZN5alloc7raw_vec12handle_error17hf5e5dfaa3433dffdE@GOTPCREL(%rip)
.LBB6_11:
.Ltmp2:
	jmp	.LBB6_13
.LBB6_12:
.Ltmp5:
.LBB6_13:
	movq	(%rsp), %rsi
	movl	$8, %edx
	movq	%r14, %rdi
	movq	%rax, %rbx
	callq	*_RNvCsIV6ETmvI9x_7___rustc14___rust_dealloc@GOTPCREL(%rip)
	movq	%rbx, %rdi
	callq	_Unwind_Resume@PLT
.Lfunc_end6:
	.size	_ZN106_$LT$criterion..routine..Function$LT$M$C$F$C$T$GT$$u20$as$u20$criterion..routine..Routine$LT$M$C$T$GT$$GT$5bench17h11cc4cbfde1703beE, .Lfunc_end6-_ZN106_$LT$criterion..routine..Function$LT$M$C$F$C$T$GT$$u20$as$u20$criterion..routine..Routine$LT$M$C$T$GT$$GT$5bench17h11cc4cbfde1703beE
	.cfi_endproc
	.section	".gcc_except_table._ZN106_$LT$criterion..routine..Function$LT$M$C$F$C$T$GT$$u20$as$u20$criterion..routine..Routine$LT$M$C$T$GT$$GT$5bench17h11cc4cbfde1703beE","a",@progbits
	.p2align	2, 0x0
