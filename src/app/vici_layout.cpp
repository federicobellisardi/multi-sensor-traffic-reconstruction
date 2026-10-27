#include <iostream>
#include <thread>
#include <chrono>
#include <vici_gui.h>

using namespace std::chrono_literals;

extern int FRAME_PER_DT;

Fl_Window *form;
Fl_Sys_Menu_Bar *menu;
gui::gl_scene *scene;
Fl_Text_Display *info_box;
Fl_Value_Slider *zoom_slider;
Fl_Check_Button *node_cid_button, *node_lid_button, *node_mark_button;
Fl_Check_Button *poly_cid_button, *poly_lid_button;
Fl_Check_Button *grid_button, *grid_mark_button;
Fl_Button *animation_button, *forward_button, *backward_button, *reset_button;
Fl_Check_Button *pawn_mark_button, *loc_mark_button, *route_mark_button;
Fl_Button *button_exit;
Fl_Text_Buffer *text_buff;

gui::gui(cart* c, simulation* s)
{
  // Get screen resolution and adjust window dimension to 90% of width and height
  int form_x, form_y, form_w, form_h;
  Fl::screen_work_area(form_x, form_y, form_w, form_h, 0);
  form_w = int(form_w * 0.9);
  form_h = int(form_h * 0.9);

  // Geometric composition parameters
  int scene_h = int(form_h * 0.9);
  int scene_w = int(form_w * 0.7);
  int button_h = int(form_h * 0.03);
  int button_w = int(form_w * 0.26);
  int spacing = int(form_h * 0.02);
  int widget_offset_h = spacing + scene_w + spacing;
  int widget_offset_v = spacing;

  // Populating widget
  text_buff = new Fl_Text_Buffer();
  form = new Fl_Window(form_x, form_y, form_w, form_h, "ViCi simulation box"); // Main window
  scene = new gl_scene(c, s, spacing, button_h + spacing, scene_w, scene_h);              // Map box

  // menu
  menu = new Fl_Sys_Menu_Bar(0, 0, form_w, button_h, "");
  menu->add("Poly/simple", "", NULL);
  menu->add("Poly/lvlps:cmap", "", NULL);
  menu->add("Poly/lvlps:closed", "", NULL);
  menu->add("Attractions/On", "", NULL);
  menu->add("Attractions/Off", "", NULL);
  menu->add("Sources/On", "", NULL);
  menu->add("Sources/Off", "", NULL);
  menu->add("Barriers/On", "", NULL);
  menu->add("Barriers/Off", "", NULL);
  menu->add("Polygons/On", "", NULL);
  menu->add("Polygons/Off", "", NULL);
  menu->callback([](Fl_Widget *p) {
    char lbl[100];
    ((Fl_Sys_Menu_Bar*)p)->item_pathname(lbl, 100);
    std::string path(lbl);
    if      (path == "Poly/simple")        scene->view_mode = MENU_VIEW_SIMPLE;
    else if (path == "Poly/lvlps:cmap")   scene->view_mode = MENU_VIEW_LVLPS_CMAP;
    else if (path == "Poly/lvlps:closed") scene->view_mode = MENU_VIEW_LVLPS_CLOSED;
    else if (path == "Attractions/On")     scene->show_attractions = true;
    else if (path == "Attractions/Off")    scene->show_attractions = false;
    else if (path == "Sources/On")         scene->show_sources = true;
    else if (path == "Sources/Off")        scene->show_sources = false;
    else if (path == "Barriers/On")        scene->show_barriers = true;
    else if (path == "Barriers/Off")       scene->show_barriers = false;
    else if (path == "Polygons/On")        scene->show_polygons = true;
    else if (path == "Polygons/Off")       scene->show_polygons = false;
    scene->reDraw = true;
  });

  // coordinates box
  info_box = new Fl_Text_Display(widget_offset_h, widget_offset_v, button_w, 10 * button_h, "info");
  info_box->wrap_mode(Fl_Text_Display::WRAP_AT_BOUNDS, Fl_Text_Display::WRAP_AT_COLUMN);
  info_box->align(FL_ALIGN_BOTTOM);
  info_box->textfont(FL_COURIER);
  info_box->textsize(11);
  text_buff->text("info box : mouse over the map to show info");
  info_box->buffer(text_buff);
  widget_offset_v += (spacing + 10 * button_h + spacing);

  // zoom button
  zoom_slider = new Fl_Value_Slider(widget_offset_h, widget_offset_v, button_w, button_h, "zoom");
  zoom_slider->type(FL_HOR_SLIDER);
  zoom_slider->bounds(0.1, 100.0);
  zoom_slider->value(scene->zoom_val);
  zoom_slider->callback([](Fl_Widget *)
  {
    scene->zoom_val = zoom_slider->value();
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h + spacing);

  // Node buttons
  node_cid_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "node cid");
  node_cid_button->callback([](Fl_Widget *)
  {
    scene->show_node_cid = !scene->show_node_cid;
    scene->reDraw = true;
  });
  node_lid_button = new Fl_Check_Button(widget_offset_h + button_w / 3, widget_offset_v, button_w / 3, button_h, "node lid");
  node_lid_button->callback([](Fl_Widget *)
  {
    scene->show_node_lid = !scene->show_node_lid;
    scene->reDraw = true;
  });
  node_mark_button = new Fl_Check_Button(widget_offset_h + 2 * button_w / 3, widget_offset_v, button_w / 3, button_h, "node mark");
  node_mark_button->value(scene->show_node_mark);
  node_mark_button->callback([](Fl_Widget *)
  {
    scene->show_node_mark = !scene->show_node_mark;
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // Poly buttons
  poly_cid_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "poly cid");
  poly_cid_button->callback([](Fl_Widget *)
  {
    scene->show_poly_cid = !scene->show_poly_cid;
    scene->reDraw = true;
  });
  poly_lid_button = new Fl_Check_Button(widget_offset_h + button_w / 3, widget_offset_v, button_w / 3, button_h, "poly lid");
  poly_lid_button->callback([](Fl_Widget *)
  {
    scene->show_poly_lid = !scene->show_poly_lid;
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // grid button
  grid_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "show grid");
  grid_button->value(scene->show_grid);
  grid_button->callback([](Fl_Widget *)
  {
    scene->show_grid = !scene->show_grid;
    scene->reDraw = true;
  });
  grid_mark_button = new Fl_Check_Button(widget_offset_h + button_w / 3, widget_offset_v, button_w / 3, button_h, "grid mark");
  grid_mark_button->value(scene->show_grid_mark);
  grid_mark_button->callback([](Fl_Widget *)
  {
    scene->show_grid_mark = !scene->show_grid_mark;
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // pawn button
  pawn_mark_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "pawn mark");
  pawn_mark_button->value(scene->show_pawn_mark);
  pawn_mark_button->callback([](Fl_Widget *)
  {
    scene->show_pawn_mark = !scene->show_pawn_mark;
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // play button
  animation_button = new Fl_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "start");
  animation_button->value(scene->animate_pawns);
  animation_button->callback([](Fl_Widget *)
  {
    scene->animate_pawns = !scene->animate_pawns;
    scene->reDraw = true;
    if   (scene->animate_pawns) animation_button->label("stop");
    else                        animation_button->label("resume");

  });
  forward_button = new Fl_Button(widget_offset_h + button_w / 3, widget_offset_v, button_w / 3, button_h, "forward");
  forward_button->callback([](Fl_Widget *)
  {
    if ( scene->pawn_idx < int(scene->pawn_history.size()-1) )++(scene->pawn_idx);
    scene->reDraw = true;
  });
  backward_button = new Fl_Button(widget_offset_h + 2 * button_w / 3, widget_offset_v, button_w / 3, button_h, "backward");
  backward_button->callback([](Fl_Widget *)
  {
    if ( scene->pawn_idx > 0 ) --(scene->pawn_idx);
    scene->reDraw = true;
  });
  widget_offset_v += (button_h);
  reset_button = new Fl_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "reset");
  reset_button->value(scene->animate_pawns);
  reset_button->callback([](Fl_Widget *)
  {
    scene->pawn_idx = 0;
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // Exit button
  button_exit = new Fl_Button(form_w - button_w / 2 - spacing, form_h - button_h - spacing, button_w / 2, button_h, "exit");
  button_exit->callback([](Fl_Widget *)
  {
    form->hide();
  });

  form->end();
  form->show();
  scene->show();

  // Register idle callback
  Fl::add_idle([](void *)
  {
    // increment frame counter
    ++(scene->frame_number);

    // undersample frame counter to evolve pawns
    if (scene->frame_number % FRAME_PER_DT == 0 && scene->animate_pawns)
    {
      if (scene->pawn_idx < int(scene->pawn_history.size() - 1)) ++(scene->pawn_idx);
      scene->reDraw = true;
    }

    // redraw if needed
    if (scene->reDraw)
    {
      scene->redraw();
      scene->update_infobox();
      scene->reDraw = !scene->reDraw;
    }
  });
}

void gui::run()
{
  // lambda wrapper is needed because run() cannot be a static method
  auto sim_thread = std::thread([](gui::gl_scene *scene){
    scene->s->run([&scene](){
      scene->pawn_history.push_back(scene->s->pawns);
    }, [](){});
  }, scene);
  Fl::run();
  sim_thread.join();
}
