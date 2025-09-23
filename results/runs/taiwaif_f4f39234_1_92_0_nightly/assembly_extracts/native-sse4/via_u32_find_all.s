# FindNeedleInHaystack Implementation: via_u32
# Target: native-sse4
# Symbol: _ZN76_$LT$benchfind..FindAllViaU32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17ha9b7f2b8a9396a01E
# Extracted: 2025-09-23T02:04:54+01:00

_ZN76_$LT$benchfind..FindAllViaU32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17ha9b7f2b8a9396a01E:
	.cfi_startproc
	leaq	3(%rdx), %r11
	movq	%rcx, %r8
	movq	%rdi, %rax
	andq	$-4, %r11
	subq	%rdx, %r11
	subq	%r11, %r8
	jae	.LBB1_2
	movl	$1, %r8d
	movl	$4, %edi
	xorl	%r9d, %r9d
	xorl	%r10d, %r10d
	jmp	.LBB1_3
.LBB1_2:
	movl	%r8d, %r10d
	movq	%r8, %r9
	leaq	(%rdx,%r11), %rdi
	andq	$-4, %r8
	movq	%r11, %rcx
	shrq	$2, %r9
	andl	$3, %r10d
	addq	%rdi, %r8
.LBB1_3:
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset %rbx, -16
	leaq	(%rdx,%rcx), %r11
	leaq	(%rdi,%r9,4), %rbx
	addq	%r8, %r10
	movq	$0, 32(%rax)
	movq	%rdi, 64(%rax)
	movq	%rbx, 72(%rax)
	movq	$0, 80(%rax)
	movb	%sil, 88(%rax)
	movq	%rdx, 96(%rax)
	movq	%rcx, 104(%rax)
	movq	%rdx, 112(%rax)
	movq	%r11, 120(%rax)
	movq	$0, 128(%rax)
	movb	%sil, 136(%rax)
	movq	$0, (%rax)
	movq	%r8, 144(%rax)
	movq	%r10, 152(%rax)
	movq	$0, 160(%rax)
	movb	%sil, 168(%rax)
	movq	%rdx, 176(%rax)
	movq	%rcx, 184(%rax)
	movq	%rdi, 192(%rax)
	movq	%r9, 200(%rax)
	popq	%rbx
	.cfi_def_cfa_offset 8
	retq
.Lfunc_end1:
	.size	_ZN76_$LT$benchfind..FindAllViaU32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17ha9b7f2b8a9396a01E, .Lfunc_end1-_ZN76_$LT$benchfind..FindAllViaU32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17ha9b7f2b8a9396a01E
	.cfi_endproc

	.section	".text._ZN76_$LT$benchfind..FindAllViaU64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hb4bb784d05055020E","ax",@progbits
	.globl	_ZN76_$LT$benchfind..FindAllViaU64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hb4bb784d05055020E
	.p2align	4
	.type	_ZN76_$LT$benchfind..FindAllViaU64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hb4bb784d05055020E,@function
