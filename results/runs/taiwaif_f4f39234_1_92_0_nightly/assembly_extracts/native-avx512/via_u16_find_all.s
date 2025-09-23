# FindNeedleInHaystack Implementation: via_u16
# Target: native-avx512
# Symbol: _ZN76_$LT$benchfind..FindAllViaU16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hc484579355deefcaE
# Extracted: 2025-09-23T02:04:56+01:00

_ZN76_$LT$benchfind..FindAllViaU16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hc484579355deefcaE:
	.cfi_startproc
	movq	%rdi, %rax
	leaq	1(%rdx), %rdi
	andq	$-2, %rdi
	subq	%rdx, %rdi
	subq	%rdi, %rcx
	jae	.LBB0_2
	movl	$1, %ecx
	movl	$2, %r8d
	xorl	%edi, %edi
	xorl	%r9d, %r9d
	xorl	%r10d, %r10d
	jmp	.LBB0_3
.LBB0_2:
	movl	%ecx, %r10d
	movq	%rcx, %r9
	leaq	(%rdx,%rdi), %r8
	andq	$-2, %rcx
	shrq	%r9
	andl	$1, %r10d
	addq	%r8, %rcx
.LBB0_3:
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset %rbx, -16
	leaq	(%rdx,%rdi), %r11
	leaq	(%r8,%r9,2), %rbx
	addq	%rcx, %r10
	movq	$0, 32(%rax)
	movq	%r8, 64(%rax)
	movq	%rbx, 72(%rax)
	movq	$0, 80(%rax)
	movb	%sil, 88(%rax)
	movq	%rdx, 96(%rax)
	movq	%rdi, 104(%rax)
	movq	%rdx, 112(%rax)
	movq	%r11, 120(%rax)
	movq	$0, 128(%rax)
	movb	%sil, 136(%rax)
	movq	$0, (%rax)
	movq	%rcx, 144(%rax)
	movq	%r10, 152(%rax)
	movq	$0, 160(%rax)
	movb	%sil, 168(%rax)
	movq	%rdx, 176(%rax)
	movq	%rdi, 184(%rax)
	movq	%r8, 192(%rax)
	movq	%r9, 200(%rax)
	popq	%rbx
	.cfi_def_cfa_offset 8
	retq
.Lfunc_end0:
	.size	_ZN76_$LT$benchfind..FindAllViaU16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hc484579355deefcaE, .Lfunc_end0-_ZN76_$LT$benchfind..FindAllViaU16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hc484579355deefcaE
	.cfi_endproc

	.section	".text._ZN76_$LT$benchfind..FindAllViaU32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17ha9b7f2b8a9396a01E","ax",@progbits
	.globl	_ZN76_$LT$benchfind..FindAllViaU32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17ha9b7f2b8a9396a01E
	.p2align	4
	.type	_ZN76_$LT$benchfind..FindAllViaU32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17ha9b7f2b8a9396a01E,@function
