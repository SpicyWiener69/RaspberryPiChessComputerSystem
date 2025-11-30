#include "lvgl.h"
#include "ui.h"
#include "nlohmann/json.hpp"

#include "src/assets/assets.h"
#include "socket_server.h"

#include <string>
#include <vector>
#include <iostream>


#define CHESS_BOARD_SIDE_LEN  400

//TODO?: getter function for globals

/* === STATIC VARIABLES ============================ */
static lv_obj_t* board_container;
static lv_obj_t* settings_menu;
static lv_obj_t* main_ui;
static lv_obj_t* menu_button;

static GameSettings game_settings = {
    false,
    1500,
    2,
    WHITE                                          
};


/* === GRID UI INTERNAL FUNCTIONS ============================ */
static std::vector<std::string> split(const std::string& s, char delim);
static const lv_image_dsc_t* piece_picker(char piece);
static void draw_on_grid(lv_obj_t* board_container,const lv_image_dsc_t* src, int col, int row);


/* === MENU UI INTERNAL FUNCTIONS ============================ */

static void init_label_with_int(lv_obj_t* label, int value, const char* fmt);

/* menu cb */
static void exit_menu_cb(lv_event_t* e);
static void engine_enable_sw_cb(lv_event_t* e);
static void engine_elo_slider_cb(lv_event_t * e);
static void engine_time_slider_cb(lv_event_t * e);
static void computer_side_sw_cb(lv_event_t* e);
static void confirm_button_cb(lv_event_t* e);

/* main page button cb */
static void menu_open_cb(lv_event_t* e);



void init_ui(void){
    main_ui = lv_obj_create(lv_screen_active());
    lv_obj_center(main_ui);
    lv_obj_set_size(main_ui,1200,1200);

    board_container = lv_obj_create(main_ui);
    settings_menu = lv_menu_create(main_ui);
    menu_button = lv_button_create(main_ui);
    
    board_grid_ui();
    open_menu_ui();
    chess_settings_menu_ui();
}


/* ======================================== */
/* === GRID UI ========================== */
/* ======================================== */


void board_grid_ui(void){
    lv_obj_t* cont = board_container;
    
    static int32_t col_dsc[] = { LV_GRID_FR(1),  LV_GRID_FR(1),  LV_GRID_FR(1),LV_GRID_FR(1),
                                LV_GRID_FR(1),  LV_GRID_FR(1),  LV_GRID_FR(1),LV_GRID_FR(1), LV_GRID_TEMPLATE_LAST};
    static int32_t row_dsc[] = { LV_GRID_FR(1),  LV_GRID_FR(1),  LV_GRID_FR(1),LV_GRID_FR(1), 
                                LV_GRID_FR(1),  LV_GRID_FR(1),  LV_GRID_FR(1),LV_GRID_FR(1), 
                                LV_GRID_TEMPLATE_LAST};

    /*Create a container with grid*/
    lv_obj_center(cont);
    lv_obj_set_style_grid_column_dsc_array(cont, col_dsc, 0);
    lv_obj_set_style_grid_row_dsc_array(cont, row_dsc, 0);
    lv_obj_set_size(cont, CHESS_BOARD_SIDE_LEN, CHESS_BOARD_SIDE_LEN);
    lv_obj_set_layout(cont, LV_LAYOUT_GRID);
    lv_obj_set_style_pad_all(cont, 0, 0);
    lv_obj_set_style_pad_row(cont,0,0);
    lv_obj_set_style_pad_column(cont,0,0);
}



void draw_fen(std::string fen){
    lv_obj_t* cont = board_container;
    lv_obj_clean(cont);
    auto rows = split(fen,'/');
    assert(rows.size() == 8);
    for (size_t i = 0; i < rows.size();++i){
        auto row = rows[i];
        std::cout << row <<'\n';
        size_t j = 0;size_t row_iter = 0;
        while (j < 8){
            char piece = row[row_iter];
            row_iter += 1;
            if(isdigit(piece)){
                // character encodings for digits are all in order from 48 (for '0') to 57 (for '9'). 
                j += piece - '0';
                continue;
            }
            else{
                const lv_image_dsc_t* src = piece_picker(piece);
                draw_on_grid(cont, src, j, i);
                j+=1;
            }
        }
    }
    std::cout << "________________" <<'\n';
}

static std::vector<std::string> split(const std::string& s, char delim) {
    std::vector<std::string> result;
    std::string current;
    for (char c : s) {
        if (c == delim) {
            result.push_back(current);
            current.clear();
        } else {
            current += c;
        }
    }
    result.push_back(current); // last token
    return result;
}

static const lv_image_dsc_t* piece_picker(char piece){
    const lv_image_dsc_t* src;
    
    switch (piece){
        /*Dark pieces*/
        case 'b':
            src = &Chess_bdt45;
            break;
        case 'k':
            src = &Chess_kdt45;
            break;
        case 'n':
            src = &Chess_ndt45;
            break;
        case 'p':
            src = &Chess_pdt45;
            break;
        case 'q':
            src = &Chess_qdt45;
            break;
        case 'r':
            src = &Chess_rdt45;
            break;

        /*light pieces*/
        case 'B':
            src = &Chess_blt45;
            break;
        case 'K':
            src = &Chess_klt45;
            break;
        case 'N':
            src = &Chess_nlt45;
            break;
        case 'P':
            src = &Chess_plt45;
            break;
        case 'Q':
            src = &Chess_qlt45;
            break;
        case 'R':
            src = &Chess_rlt45;
            break;

        default:
            src = &Chess_kdt45;
        break;

    }
    return src;
}

static void draw_on_grid(lv_obj_t* cont,const lv_image_dsc_t* src, int col, int row){
    lv_obj_t* img = lv_image_create(cont);
    lv_image_set_src(img, src);

    lv_coord_t img_width = lv_image_get_src_width(img);
    lv_coord_t img_height = lv_image_get_src_height(img);
    int target_w = CHESS_BOARD_SIDE_LEN / 8;
    int target_h = CHESS_BOARD_SIDE_LEN / 8;
    float zoom_w = (float)target_w / img_width;
    float zoom_h = (float)target_h / img_height;
    float z = zoom_w < zoom_h ? zoom_w : zoom_h;
    uint16_t zoom = (uint16_t)(z * 256);

    lv_image_set_scale(img, zoom);
    lv_obj_set_grid_cell(img, LV_GRID_ALIGN_STRETCH, col, 1,
            LV_GRID_ALIGN_STRETCH, row, 1);
}

/* ======================================== */
/* === MENU UI ========================== */
/* ======================================== */



void open_menu_ui(void){
    //lv_obj_t* button = lv_button_create(lv_screen_active());
    lv_obj_t* button = menu_button;
    lv_obj_align(menu_button, LV_ALIGN_TOP_RIGHT, 0, 0);
    lv_obj_t* label;
    label = lv_label_create(button);          
    lv_label_set_text(label, "Game Settings");              
    lv_obj_center(label);
    lv_obj_add_event_cb(button, menu_open_cb, LV_EVENT_CLICKED, NULL);
}

static void menu_open_cb(lv_event_t* e){
    lv_obj_t* menu = settings_menu;
    //lv_obj_t * button = lv_event_get_target_obj(e);
    lv_event_code_t code = lv_event_get_code(e);
   
    if(code == LV_EVENT_CLICKED) {
       lv_obj_remove_flag(menu,LV_OBJ_FLAG_HIDDEN); 
    }
}


void chess_settings_menu_ui(void){   
    /*Create a menu object*/
    //menu = lv_menu_create(lv_screen_active());
    
    lv_obj_t* menu = settings_menu;

    lv_obj_set_size(menu, 500, 800);

    //lv_obj_center(menu);
    
    lv_obj_align(menu, LV_ALIGN_TOP_RIGHT, 0,100);
    lv_obj_set_style_bg_color(menu,lv_color_hex(0xFFFFCC), LV_PART_MAIN);
    lv_menu_set_mode_root_back_button(menu, LV_MENU_ROOT_BACK_BUTTON_ENABLED);
    lv_obj_add_event_cb(menu, exit_menu_cb, LV_EVENT_CLICKED, menu);
    
    /* hide menu at init*/
    lv_obj_add_flag(menu, LV_OBJ_FLAG_HIDDEN);

    /*Modify the header*/
    lv_obj_t * back_btn = lv_menu_get_main_header_back_button(menu);
    lv_obj_t * back_button_label = lv_label_create(back_btn);
    lv_label_set_text(back_button_label, "Back");

    lv_obj_t * cont;
    lv_obj_t * label;

    /*
    Create the engine settings page
    */
    lv_obj_t * engine_page = lv_menu_page_create(menu, "Page 1");

    cont = lv_menu_cont_create(engine_page);
    label = lv_label_create(cont);
    lv_label_set_text(label, "enable engine");
    
    cont = lv_menu_cont_create(engine_page);
    lv_obj_t* engine_enable_sw = lv_switch_create(cont);
    lv_obj_t* engine_section =  lv_menu_section_create(engine_page);
    lv_obj_add_event_cb(engine_enable_sw, engine_enable_sw_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_set_user_data(engine_enable_sw, engine_section);
    

    /*strength settings*/
    cont = lv_menu_cont_create(engine_section);
    label = lv_label_create(cont);
    lv_label_set_text(label, "engine strength");
    
    cont = lv_menu_cont_create(engine_section);
    lv_obj_t * elo_slider = lv_slider_create(cont);
    lv_slider_set_range(elo_slider, 400, 2500);
    lv_slider_set_value(elo_slider,game_settings.engine_strength,LV_ANIM_OFF);
    lv_obj_add_event_cb(elo_slider, engine_elo_slider_cb, LV_EVENT_CLICKED, NULL);
    label = lv_label_create(cont);
    int elo = game_settings.engine_strength;
    init_label_with_int(label,elo,"%d ELO");
    lv_obj_set_user_data(elo_slider, label);

    /*timing settings*/
    cont = lv_menu_cont_create(engine_section);
    label = lv_label_create(cont);
    lv_label_set_text(label, "engine time");

    cont = lv_menu_cont_create(engine_section);
    lv_obj_t * time_slider = lv_slider_create(cont);
    lv_slider_set_range(time_slider, 1, 10);
    lv_slider_set_value(time_slider,game_settings.engine_timeout,LV_ANIM_OFF);
    lv_obj_add_event_cb(time_slider, engine_time_slider_cb, LV_EVENT_CLICKED, NULL);
    label = lv_label_create(cont);
    int time = game_settings.engine_timeout;
    init_label_with_int(label,time,"%d s");
    lv_obj_set_user_data(time_slider, label);

    /*play side settings*/
    cont = lv_menu_cont_create(engine_section);
    label = lv_label_create(cont);
    lv_label_set_text(label, "engine side");

    cont = lv_menu_cont_create(engine_section);
    lv_obj_t* side_sw = lv_switch_create(cont);
    lv_obj_add_event_cb(side_sw,computer_side_sw_cb,LV_EVENT_CLICKED,NULL);
    label = lv_label_create(cont);
    (game_settings.side == BLACK)? lv_label_set_text(label, "Black"):lv_label_set_text(label, "White"); 
    lv_obj_set_user_data(side_sw, label);
    
    cont = lv_menu_cont_create(engine_section);
    lv_obj_t* confirm_button = lv_button_create(cont);
    label = lv_label_create(confirm_button);          
    lv_label_set_text(label, "Confirm");              
    lv_obj_center(label);
    lv_obj_add_event_cb(confirm_button,confirm_button_cb,LV_EVENT_CLICKED,menu);
    
    /*hide the engine settings at init*/
    lv_obj_add_flag(engine_section, LV_OBJ_FLAG_HIDDEN);
    

    /*
    Create the PvP settings page
    */

    lv_obj_t * board_page = lv_menu_page_create(menu, "Page 2");
    cont = lv_menu_cont_create(board_page);
    label = lv_label_create(cont);
    lv_label_set_text(label, "eeeeeeee");
    
    cont = lv_menu_cont_create(board_page);
    label = lv_label_create(cont);
    lv_label_set_text(label, "aaaaaaaaaaa");
    

    /*Create a main page*/
    lv_obj_t * main_page = lv_menu_page_create(menu, NULL);
    cont = lv_menu_cont_create(main_page);
    label = lv_label_create(cont);
    lv_label_set_text(label, "Chess Engine Settings");
    lv_menu_set_load_page_event(menu, cont, engine_page);

    cont = lv_menu_cont_create(main_page);
    label = lv_label_create(cont);
    lv_label_set_text(label, "Board color settings");
    lv_menu_set_load_page_event(menu, cont, board_page);

    lv_menu_set_page(menu, main_page);
}


static void engine_enable_sw_cb(lv_event_t * e){   
    lv_obj_t * swt = lv_event_get_target_obj(e);
    //lv_obj_t* cont = lv_obj_get_parent(swt);
    lv_obj_t* engine_menu = (lv_obj_t *)lv_obj_get_user_data(swt);
    if (!engine_menu) return;

    if (lv_obj_has_state(swt, LV_STATE_CHECKED)){
        lv_obj_remove_flag(engine_menu,LV_OBJ_FLAG_HIDDEN);
        game_settings.computer_playing = true;
    }
    else{
        lv_obj_add_flag(engine_menu, LV_OBJ_FLAG_HIDDEN);
        game_settings.computer_playing = false;
    }
}

static void engine_elo_slider_cb(lv_event_t * e){   
    lv_obj_t* slider = lv_event_get_target_obj(e);
    lv_obj_t* elo_label = (lv_obj_t*)lv_obj_get_user_data(slider);
    int elo = (int)lv_slider_get_value(slider);
    if (!elo_label) return;
    init_label_with_int(elo_label,elo,"%d ELO");
}

static void engine_time_slider_cb(lv_event_t * e){   
    lv_obj_t* slider = lv_event_get_target_obj(e);
    lv_obj_t* time_label = (lv_obj_t*)lv_obj_get_user_data(slider);
    int elo = (int)lv_slider_get_value(slider);
    if (!time_label) return;
    init_label_with_int(time_label,elo,"%d s");
}


static void computer_side_sw_cb(lv_event_t* e){
    lv_obj_t * sw = lv_event_get_target_obj(e);
    
    lv_obj_t* side_label = (lv_obj_t *)lv_obj_get_user_data(sw);
    if (!side_label) return;
    if (lv_obj_has_state(sw, LV_STATE_CHECKED)){
        game_settings.side = BLACK;
        lv_label_set_text(side_label, "Black");
    }
    else{
        game_settings.side = WHITE;
        lv_label_set_text(side_label, "White");
    }
}

static void confirm_button_cb(lv_event_t* e){
    //lv_obj_t * button = lv_event_get_target_obj(e);
    lv_event_code_t code = lv_event_get_code(e);
    char* buf = "hello";
    int len = 6;
    if(code == LV_EVENT_CLICKED) { 
        /* socket send */
        socket_send_string(buf, len);


        /* hide menu*/
        lv_obj_t* menu = (lv_obj_t *)lv_event_get_user_data(e);
        lv_obj_add_flag(menu, LV_OBJ_FLAG_HIDDEN);

    }
}

static void exit_menu_cb(lv_event_t * e){   
    lv_obj_t * obj = lv_event_get_target_obj(e);
    lv_obj_t * menu = (lv_obj_t *)lv_event_get_user_data(e);

    if(lv_menu_back_button_is_root(menu, obj)) {
        lv_obj_add_flag(menu, LV_OBJ_FLAG_HIDDEN);
    }
}

static void init_label_with_int(lv_obj_t* label, int value, const char* fmt){
    char buf[32];
    lv_snprintf(buf, sizeof(buf), fmt, value);
    lv_label_set_text(label, buf);
}
