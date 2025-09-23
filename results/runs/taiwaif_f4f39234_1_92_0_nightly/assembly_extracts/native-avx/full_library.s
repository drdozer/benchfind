	.file	"benchfind.3f43fb39528a462d-cgu.0"
	.section	".text._ZN76_$LT$benchfind..FindAllViaU16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hc484579355deefcaE","ax",@progbits
	.globl	_ZN76_$LT$benchfind..FindAllViaU16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hc484579355deefcaE
	.p2align	4
	.type	_ZN76_$LT$benchfind..FindAllViaU16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hc484579355deefcaE,@function
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
_ZN76_$LT$benchfind..FindAllViaU64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hb4bb784d05055020E:
	.cfi_startproc
	leaq	7(%rdx), %r11
	movq	%rcx, %r8
	movq	%rdi, %rax
	andq	$-8, %r11
	subq	%rdx, %r11
	subq	%r11, %r8
	jae	.LBB2_2
	movl	$1, %r8d
	movl	$8, %edi
	xorl	%r9d, %r9d
	xorl	%r10d, %r10d
	jmp	.LBB2_3
.LBB2_2:
	movl	%r8d, %r10d
	movq	%r8, %r9
	leaq	(%rdx,%r11), %rdi
	andq	$-8, %r8
	movq	%r11, %rcx
	shrq	$3, %r9
	andl	$7, %r10d
	addq	%rdi, %r8
.LBB2_3:
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset %rbx, -16
	leaq	(%rdx,%rcx), %r11
	leaq	(%rdi,%r9,8), %rbx
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
.Lfunc_end2:
	.size	_ZN76_$LT$benchfind..FindAllViaU64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hb4bb784d05055020E, .Lfunc_end2-_ZN76_$LT$benchfind..FindAllViaU64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hb4bb784d05055020E
	.cfi_endproc

	.section	".text._ZN79_$LT$benchfind..FindAllViaSimd16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h988827eea7004512E","ax",@progbits
	.globl	_ZN79_$LT$benchfind..FindAllViaSimd16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h988827eea7004512E
	.p2align	4
	.type	_ZN79_$LT$benchfind..FindAllViaSimd16$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h988827eea7004512E,@function
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
_ZN79_$LT$benchfind..FindAllViaSimd32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hd7127a3e58e3fd06E:
	.cfi_startproc
	leaq	31(%rdx), %r11
	movq	%rcx, %r8
	movq	%rdi, %rax
	andq	$-32, %r11
	subq	%rdx, %r11
	subq	%r11, %r8
	jae	.LBB4_2
	movl	$1, %r8d
	movl	$32, %edi
	xorl	%r9d, %r9d
	xorl	%r10d, %r10d
	jmp	.LBB4_3
.LBB4_2:
	movl	%r8d, %r10d
	movq	%r8, %r9
	leaq	(%rdx,%r11), %rdi
	andq	$-32, %r8
	movq	%r11, %rcx
	shrq	$5, %r9
	andl	$31, %r10d
	addq	%rdi, %r8
.LBB4_3:
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset %rbx, -16
	movq	%r9, %rbx
	leaq	(%rdx,%rcx), %r11
	addq	%r8, %r10
	movq	$0, (%rax)
	movq	$0, 24(%rax)
	movq	%rdi, 48(%rax)
	shlq	$5, %rbx
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
.Lfunc_end4:
	.size	_ZN79_$LT$benchfind..FindAllViaSimd32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hd7127a3e58e3fd06E, .Lfunc_end4-_ZN79_$LT$benchfind..FindAllViaSimd32$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17hd7127a3e58e3fd06E
	.cfi_endproc

	.section	".text._ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E","ax",@progbits
	.globl	_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E
	.p2align	4
	.type	_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E,@function
_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E:
	.cfi_startproc
	leaq	63(%rdx), %r11
	movq	%rcx, %r8
	movq	%rdi, %rax
	andq	$-64, %r11
	subq	%rdx, %r11
	subq	%r11, %r8
	jae	.LBB5_2
	movl	$1, %r8d
	movl	$64, %edi
	xorl	%r9d, %r9d
	xorl	%r10d, %r10d
	jmp	.LBB5_3
.LBB5_2:
	movl	%r8d, %r10d
	movq	%r8, %r9
	leaq	(%rdx,%r11), %rdi
	andq	$-64, %r8
	movq	%r11, %rcx
	shrq	$6, %r9
	andl	$63, %r10d
	addq	%rdi, %r8
.LBB5_3:
	pushq	%rbx
	.cfi_def_cfa_offset 16
	.cfi_offset %rbx, -16
	movq	%r9, %rbx
	leaq	(%rdx,%rcx), %r11
	addq	%r8, %r10
	movq	$0, (%rax)
	movq	$0, 24(%rax)
	movq	%rdi, 48(%rax)
	shlq	$6, %rbx
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
.Lfunc_end5:
	.size	_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E, .Lfunc_end5-_ZN79_$LT$benchfind..FindAllViaSimd64$u20$as$u20$benchfind..FindNeedleInHaystack$GT$8find_all17h815df586cbbb76a6E
	.cfi_endproc

	.ident	"rustc version 1.92.0-nightly (9f32ccf35 2025-09-21)"
	.section	".note.GNU-stack","",@progbits
