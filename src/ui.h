/**
 * @file ui.h
 *
 * Chess ui definitions
 *
 * Author: 
 *
 */
#ifndef UI_H
#define UI_H


#include <string>
#include "lvgl.h"

void init_ui(void);

/* === GRID UI EXTERNAL FUNCTIONS ============================ */

void board_grid_ui(void);
void draw_fen(std::string fen);


/* === MENU UI EXTERNAL FUNCTIONS ============================ */

void chess_settings_menu_ui(void);
void open_menu_ui(void);


/* === DEFINITIONS ============================ */


typedef enum{
    NONE,
    BLACK,
    WHITE
}Side;

typedef struct{
    bool computer_playing;
    int engine_timeout;
    int engine_strength;
    Side side;
}GameSettings;









#endif 
