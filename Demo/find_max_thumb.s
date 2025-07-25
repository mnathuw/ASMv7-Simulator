.text

push {r0, r1, r2, r3, r4}
ldr r0, =array
ldr r1, =length
ldr r1, [r1]
mov r2, #0
ldr r3, [r0]

loop:
    add r2, r2, #1
    cmp r2, r1
    beq done

    lsl r4, r2, #2
    ldr r4, [r0, r4]

    cmp r4, r3
    ble loop

    mov r3, r4

    b loop

done:
pop {r0, r1, r2, r3, r4}

.data
array:  .word 5, 1, 4, 2, 8, -7
length: .word 6
