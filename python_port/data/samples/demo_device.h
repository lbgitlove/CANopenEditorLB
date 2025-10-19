/*
 * CANopenNode object dictionary header
 * Generated: 2023-01-01 00:00:00Z
 */
#ifndef CO_OD_H
#define CO_OD_H

#include <stdint.h>

extern uint32_t OD_1000;
extern uint8_t OD_1001;

typedef struct {
    uint8_t Number_of_mapped_objects; /* sub0 */
    uint32_t Mapped_object_1; /* sub1 */
    uint32_t Mapped_object_2; /* sub2 */
} OD_1600_t;
extern OD_1600_t OD_1600;

#endif /* CO_OD_H */
