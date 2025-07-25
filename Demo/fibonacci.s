.text

fibonacci:
    push {r0, r1, r2, r3, r4, r5, r6}
    ldr r0, =n
    ldr r1, [r0]
    mov r2, #0
    mov r3, #1
    mov r4, #0
    ldr r5, =result

    cmp r1, #0
    beq store_zero_fib

    cmp r1, #1
    beq store_one_fib

loop_fib:
    cmp r4, r1
    beq end_fib

    str r2, [r5, r4, lsl #2]

    add r6, r2, r3
    mov r2, r3
    mov r3, r6

    add r4, r4, #1
    b loop_fib

store_zero_fib:
    str r2, [r5]
    b end_fib

store_one_fib:
    str r3, [r5]
    b end_fib

end_fib:
    pop {r0, r1, r2, r3, r4, r5, r6}

reverse_array:
    push {r0, r1, r2, r3, r4, r5, r6, r7}
    ldr r0, =result
    ldr r1, =array_reverse
    ldr r2, [r0]
    ldr r4, =n
    ldr r4, [r4]
    sub r4, #1

counter_reverse:
    cmp r4, r5
    beq stopcounting_reverse
    add r5, r5, #1
    add r0, r0, #4
    b counter_reverse

stopcounting_reverse:
    mov r6, r5
    mov r7, r4

swap_reverse:
    ldr r3, [r0]
    str r3, [r1]
    sub r6, r6, #1
    add r1, r1, #4
    sub r0, r0, #4
    cmp r7, #0
    beq exit_reverse
    sub r7, r7, #1
    b swap_reverse

exit_reverse:
    pop {r0, r1, r2, r3, r4, r5, r6, r7}

.data
n: .word 10
return: .zero 4
result: .space 40
array_reverse: .skip 40