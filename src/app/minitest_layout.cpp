#include <iostream>
#include <minitest_gui.h>

Fl_Window *form;
Fl_Sys_Menu_Bar *menu;
gui::gl_scene *scene;
Fl_Text_Display *info_box;
Fl_Value_Slider *zoom_slider;
Fl_Check_Button *node_cid_button, *node_lid_button, *node_mark_button;
Fl_Check_Button *poly_cid_button, *poly_lid_button;
Fl_Check_Button *subgraph_button, *select_button;
Fl_Input *select_input;
Fl_Check_Button *pointproj_button;
Fl_Button *pointproj_reset_button;
Fl_Check_Button *grid_button, *grid_mark_button;
Fl_Check_Button *arc_mark_button;
Fl_Button *arc_reset_button;
Fl_Check_Button *dijk_show_button;
Fl_Button *dijk_reset_button;
Fl_Button *animation_button;
Fl_Check_Button *polyinsquare_button, *polyusage_button;
Fl_Button *button_exit;
Fl_Text_Buffer *text_buff;

gui::gui(cart* c)
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
  form = new Fl_Window(form_x, form_y, form_w, form_h, "minimocas debug box"); // Main window
  scene = new gl_scene(c, spacing, spacing, scene_w, scene_h);              // Map box

  // menu
  menu = new Fl_Sys_Menu_Bar(0, 0, spacing, spacing, "");
  menu->add("View/simple", "", NULL);
  menu->add("View/lvl ps", "", NULL);
  menu->callback([](Fl_Widget* p) {
    char lbl[100];
    ((Fl_Sys_Menu_Bar*)p)->item_pathname(lbl, 100);
    std::string path(lbl);
    if ( path == "View/simple" )
      scene->view_mode = MENU_VIEW_SIMPLE;
    else if ( path == "View/lvl ps" )
      scene->view_mode = MENU_VIEW_LVLPS;
    scene->reDraw = true;
  });

  // coordinates box
  info_box = new Fl_Text_Display(widget_offset_h, widget_offset_v, button_w, 10 * button_h, "info");
  info_box->wrap_mode(Fl_Text_Display::WRAP_AT_BOUNDS, Fl_Text_Display::WRAP_AT_COLUMN);
  info_box->align(FL_ALIGN_BOTTOM);
  info_box->textfont(FL_COURIER);
  info_box->textsize(11);
  text_buff->text("info box : mouse over the map to view content");
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

  // Subgraph and Select buttons
  subgraph_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "show subgraph");
  subgraph_button->callback([](Fl_Widget *) {
    scene->show_subgraph = !scene->show_subgraph;
    scene->reDraw = true;
  });
  select_button = new Fl_Check_Button(widget_offset_h + button_w / 3, widget_offset_v, button_w / 3, button_h, "select");
  select_button->callback([](Fl_Widget *) {
    scene->show_select = !scene->show_select;
    scene->reDraw = true;
  });
  select_input = new Fl_Input(widget_offset_h + 2 * button_w / 3, widget_offset_v, button_w / 3, button_h, "");
  widget_offset_v += (spacing + button_h);

  // point projection button
  pointproj_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "show point proj");
  pointproj_button->value(scene->show_pointproj_mark);
  pointproj_button->callback([](Fl_Widget *)
  {
    scene->show_pointproj_mark = !scene->show_pointproj_mark;
    scene->reDraw = true;
  });
  pointproj_reset_button = new Fl_Button(widget_offset_h + 2 * button_w / 3, widget_offset_v, button_w / 3, button_h, "reset point proj");
  pointproj_reset_button->callback([](Fl_Widget *)
  {
    scene->currentpt1.clear();
    scene->currentpt2.clear();
    scene->currentptproj1.clear();
    scene->currentptproj2.clear();
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

  // arc button
  arc_mark_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "show arc mark");
  arc_mark_button->value(scene->show_arc_mark);
  arc_mark_button->callback([](Fl_Widget *)
  {
    scene->show_arc_mark = !scene->show_arc_mark;
    scene->reDraw = true;
  });
  arc_reset_button = new Fl_Button(widget_offset_h + 2 * button_w / 3, widget_offset_v, button_w / 3, button_h, "reset link view");
  arc_reset_button->callback([](Fl_Widget *)
  {
    scene->currenta = scene->c->arc.end();
    scene->currentpoly.clear();
    scene->update_infobox();
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // dijkstra button
  dijk_show_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "show dijkstra");
  dijk_show_button->value(scene->show_dijkstra);
  dijk_show_button->callback([](Fl_Widget *)
  {
    scene->show_dijkstra = !scene->show_dijkstra;
    scene->reDraw = true;
  });
  dijk_reset_button = new Fl_Button(widget_offset_h + 2 * button_w / 3, widget_offset_v, button_w / 3, button_h, "reset dijkstra");
  dijk_reset_button->callback([](Fl_Widget *)
  {
    scene->dijkstra_node.clear();
    scene->dijkstra_point.clear();
    scene->dijkstra_status = -2;
    scene->currentn1.clear();
    scene->currentn2.clear();
    scene->currentpt1.clear();
    scene->currentptproj1.clear();
    scene->currentpt2.clear();
    scene->currentptproj2.clear();
    scene->currentptv.clear();
    scene->update_infobox();
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // animate button
  animation_button = new Fl_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "");
  animation_button->label("@+3>");
  animation_button->callback([](Fl_Widget *)
  {
    scene->enable_animation = !scene->enable_animation;
    if   (scene->enable_animation) animation_button->label("@+3||");
    else                           animation_button->label("@+3>");
    scene->reDraw = true;
  });
  widget_offset_v += (spacing + button_h);

  // poly in square button
  polyinsquare_button = new Fl_Check_Button(widget_offset_h, widget_offset_v, button_w / 3, button_h, "show poly square");
  //polyinsquare_button->value(scene->show_polyinsquare_mark);
  polyinsquare_button->callback([](Fl_Widget *)
  {
    scene->show_polyinsquare_mark = !scene->show_polyinsquare_mark;
    scene->reDraw = true;
  });
  polyusage_button = new Fl_Check_Button(widget_offset_h + 2 * button_w / 3, widget_offset_v, button_w / 3, button_h, "show poly usage");
  //polyusage_button->value(scene->show_polyusage);
  polyusage_button->callback([](Fl_Widget *)
  {
    scene->show_polyusage = !scene->show_polyusage;
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
    if (scene->enable_animation)
    {
      if( scene->frame_number % 1 == 0 )  scene->bitpattFT = (scene->bitpattFT << 1) | (scene->bitpattFT >> 15);  // left cyclic bit shift
      if( scene->frame_number % 30 == 0 ) scene->bitpattTF = (scene->bitpattTF >> 1) | (scene->bitpattTF << 15);  // right cyclic bit shift
    }

    if (scene->reDraw)
    {
      if( !scene->enable_animation ) scene->reDraw = false;
      scene->redraw();
    }
  });
}

void gui::run() { Fl::run(); }
