/*!
 *  \file   minitest_gui.h
 *  \author A. Fabbri (alessandro.fabbri27@unibo.it), C. Mizzi (chiara.mizzi2@unibo.it)
 *  \brief  Support header for the graphical part of `minitest` app.
 *  \details This support header file contains the principal definition for the graphical part of `minitest` app.
 */

#include <FL/Fl.H>
#include <FL/gl.h>
#include <FL/glu.h>
#include <FL/Fl_Box.H>
#include <FL/Fl_Button.H>
#include <FL/Fl_Check_Button.H>
#include <FL/Fl_Gl_Window.H>
#include <FL/Fl_Output.H>
#include <FL/Fl_Round_Button.H>
#include <FL/Fl_Slider.H>
#include <FL/Fl_Text_Display.H>
#include <FL/Fl_Value_Slider.H>
#include <FL/Fl_Window.H>
#include <FL/Fl_Menu_Item.H>
#include <FL/Fl_Menu_Bar.H>
#include <FL/Fl_Sys_Menu_Bar.H>

#include <carto.h>

///////////////////////////////////////////////////////////////
////// FLTK GUI CLASS
///////////////////////////////////////////////////////////////

#define FRAME_PER_DT      2000

enum
{
  MENU_VIEW_SIMPLE = 0,
  MENU_VIEW_LVLPS,
};

class gui
{
public:
  gui(cart* c);
  void run();

  class gl_scene : public Fl_Gl_Window
  {
  public:
    gl_scene(cart* _cptr, int x, int y, int w, int h, const char *l = 0);
    void draw();
    int handle(int event);

    inline void screen_to_coord(int &ilat, int &ilon)
    {
      ilat = int( ((this->h() - Fl::event_y()) * 2. * dilat / this->h() - dilat) / zoom_val + ilatcen );
      ilon = int( (Fl::event_x() * 2. * dilon / this->w() - dilon) / zoom_val + iloncen );
    }
    inline void screen_to_coord(point_base &pt) { screen_to_coord(pt.ilat, pt.ilon); }

    void update_infobox();

  private:
    friend class gui;
    cart *c;
    int ilatmin, ilatmax, ilonmin, ilonmax;
    int iloncen, ilatcen, dilat, dilon;
    int lateps, loneps;

    double zoom_val;
    int ilatshift, ilonshift, ilatorig, ilonorig;

    bool reDraw;
    point_base mousept;
    int mouserow, mousecol;
    arc_it currenta;
    std::vector<node_it> currentn1, currentn2;
    std::vector<point_base> currentpt1, currentpt2, currentptv;
    std::vector<point_proj> currentptproj1, currentptproj2;
    std::vector<poly_it> currentpoly;
    std::vector<path_base> dijkstra_node;
    std::vector<path_point> dijkstra_point;
    int dijkstra_status;
    std::string select_content;

    bool show_node_cid, show_node_lid, show_node_mark;
    bool show_poly_cid, show_poly_lid;
    bool show_subgraph, show_select;
    bool show_arc_mark;
    bool show_pointproj_mark;
    bool show_grid, show_grid_mark;
    bool show_dijkstra;
    bool show_polyinsquare_mark, show_polyusage;
    bool enable_animation;
    int view_mode;

    unsigned short bitpattFT, bitpattTF;
    unsigned short shiftFT, shiftTF;
    unsigned long long int frame_number;

    // draw whole scene
    void draw_scene();
    // draw components
    void draw_cart();
    void draw_node_cid();
    void draw_node_lid();
    void draw_node_mark();
    void draw_poly_cid();
    void draw_poly_lid();
    void draw_subgraph();
    void draw_select();
    void draw_link_mark();
    void draw_grid();
    void draw_grid_mark();
    void draw_dijkstra();
    void draw_pointproj();
    void draw_poly_insquare();
    void draw_poly_usage();

    // draw basic object
    template<typename... Args> void draw(const Args &...args);
    void draw_line(const point_base &pt1, const point_base &pt2);
  };
};
