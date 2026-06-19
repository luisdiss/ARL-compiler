.section __TEXT,__text
.global _main
.align 4

_fol:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    sub sp, sp, #32
    str x0, [x29, #-8]
    ldr x0, [x29, #-8]
    str x0, [x29, #-16]
    mov x0, #2
    mov x1, #3
    mul x0, x0, x1
    str x0, [x29, #-24]
    ldr x0, [x29, #-16]
    ldr x1, [x29, #-24]
    add x0, x0, x1
    str x0, [x29, #-32]
    ldr x0, [x29, #-32]
    mov sp, x29
    ldp x29, x30, [sp], #16
    ret

_main:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    sub sp, sp, #48
    mov x0, #1
    bl _fol
    str x0, [x29, #-8]
    mov x0, #1
    mov x1, #2
    cmp x0, x1
    cset x0, lt
    str x0, [x29, #-16]
    mov x0, #2
    mov x1, #3
    cmp x0, x1
    cset x0, gt
    str x0, [x29, #-24]
    ldr x0, [x29, #-16]
    ldr x1, [x29, #-24]
    and x0, x0, x1
    str x0, [x29, #-32]
    ldr x0, [x29, #-32]
    cbz x0, if_0_end
    b if_0_body
if_0_body:
    mov x0, #8
    str x0, [x29, #-40]
    b if_0_end
if_0_end:
    mov x0, #0
    mov sp, x29
    ldp x29, x30, [sp], #16
    ret
