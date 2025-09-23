# FindNeedleInHaystack Implementation: via_simd64
# Target: default
# Symbol: _ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E
# Extracted: 2025-09-23T02:04:53+01:00

_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E:
	.cfi_startproc
	movq	%rdi, %rax
	leaq	63(%rdx), %r11
	andq	$-64, %r11
	subq	%rdx, %r11
	movq	%rcx, %r8
	subq	%r11, %r8
	jae	.LBB5_2
	movl	$1, %r8d
	movl	$64, %edi
	xorl	%r9d, %r9d
	xorl	%r10d, %r10d
	jmp	.LBB5_3
.LBB5_2:
	leaq	(%rdx,%r11), %rdi
	movq	%r8, %r9
	shrq	$6, %r9
	movl	%r8d, %r10d
	andl	$63, %r10d
	andq	$-64, %r8
	addq	%rdi, %r8
	movq	%r11, %rcx
.LBB5_3:
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset %rbx, -16
	leaq	(%rdx,%rcx), %r11
	movq	%r9, %rbx
	shlq	$6, %rbx
	addq	%rdi, %rbx
	addq	%r8, %r10
	movq	$0, (%rax)
	movq	$0, 24(%rax)
	movq	%rdi, 48(%rax)
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
.Lfunc_end5:
	.size	_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E, .Lfunc_end5-_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E
	.cfi_endproc

	.ident	"rustc version 1.92.0-nightly (9f32ccf35 2025-09-21)"
	.section	".note.GNU-stack","",@progbits
