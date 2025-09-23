# FindNeedleInHaystack Implementation: via_simd16
# Target: native-avx512
# Symbol: _ZN79_$LT$benchfind..FindAllViaSimd16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h988827eea7004512E
# Extracted: 2025-09-23T02:04:56+01:00

_ZN79_$LT$benchfind..FindAllViaSimd16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h988827eea7004512E:
	.cfi_startproc
	leaq	15(%rdx), %r11
	movq	%rcx, %r8
	movq	%rdi, %rax
	andq	$-16, %r11
	subq	%rdx, %r11
	subq	%r11, %r8
	jae	.LBB3_2
	movl	$1, %r8d
	movl	$16, %edi
	xorl	%r9d, %r9d
	xorl	%r10d, %r10d
	jmp	.LBB3_3
.LBB3_2:
	movl	%r8d, %r10d
	movq	%r8, %r9
	leaq	(%rdx,%r11), %rdi
	andq	$-16, %r8
	movq	%r11, %rcx
	shrq	$4, %r9
	andl	$15, %r10d
	addq	%rdi, %r8
.LBB3_3:
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset %rbx, -16
	movq	%r9, %rbx
	leaq	(%rdx,%rcx), %r11
	addq	%r8, %r10
	movq	$0, (%rax)
	movq	$0, 24(%rax)
	movq	%rdi, 48(%rax)
	shlq	$4, %rbx
	addq	%rdi, %rbx
	movq	%rbx, 56(%rax)
	movq	$0, 64(%rax)
	movb	%sil, 72(%rax)
	movq	%rdx, 80(%rax)
	movq	%rcx, 88(%rax)
	movq	%rdx, 96(%rax)
	movq	%r11, 104(%rax)
	movq	$0, 112(%rax)
	movb	%sil, 120(%rax)
	movq	%r8, 128(%rax)
	movq	%r10, 136(%rax)
	movq	$0, 144(%rax)
	movb	%sil, 152(%rax)
	movq	%rdx, 160(%rax)
	movq	%rcx, 168(%rax)
	movq	%rdi, 176(%rax)
	movq	%r9, 184(%rax)
	popq	%rbx
	.cfi_def_cfa_offset 8
	retq
.Lfunc_end3:
	.size	_ZN79_$LT$benchfind..FindAllViaSimd16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h988827eea7004512E, .Lfunc_end3-_ZN79_$LT$benchfind..FindAllViaSimd16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h988827eea7004512E
	.cfi_endproc

	.section	".text._ZN79_$LT$benchfind..FindAllViaSimd32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hd7127a3e58e3fd06E","ax",@progbits
	.globl	_ZN79_$LT$benchfind..FindAllViaSimd32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hd7127a3e58e3fd06E
	.p2align	4
	.type	_ZN79_$LT$benchfind..FindAllViaSimd32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hd7127a3e58e3fd06E,@function
