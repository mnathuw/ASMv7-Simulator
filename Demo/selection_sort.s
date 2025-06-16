.text

main:
    push {r0, r1, r2, r3, r4, r5, r6}
    ldr r0, =list
    ldr r1, =length
    ldr r1, [r1]
    sub r1, r1, #1
    mov r2, #0

outer_loop:
    cmp r2, r1
    bge sort_done

    mov r3, r2
    add r4, r2, #1

inner_loop:
    cmp r4, r1
    bgt inner_done

    ldr r5, [r0, r4, lsl #2]
    ldr r6, [r0, r3, lsl #2]
    cmp r5, r6
    bge skip_update
    mov r3, r4

skip_update:
    add r4, r4, #1
    b inner_loop

inner_done:
    ldr r5, [r0, r2, lsl #2]
    ldr r6, [r0, r3, lsl #2]
    str r6, [r0, r2, lsl #2]
    str r5, [r0, r3, lsl #2]

    add r2, r2, #1
    b outer_loop

sort_done:
    pop {r0, r1, r2, r3, r4, r5, r6}

.data
list:   .word 5, 1, 4, 2, 8, -7
length: .word 6
