#include <vector>

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
#include <FL/Fl_Sys_Menu_Bar.H>

#include <physycom/time.hpp>

#include <carto.h>
#include <pawn.h>
#include <simulation.h>

///////////////////////////////////////////////////////////////
////// FLTK GUI CLASS
///////////////////////////////////////////////////////////////

enum
{
  MENU_VIEW_SIMPLE = 0,
  MENU_VIEW_LVLPS_CMAP,
  MENU_VIEW_LVLPS_CLOSED,
};

class gui
{
public:
  gui(cart* c, simulation *_s);
  void run();

  class gl_scene : public Fl_Gl_Window
  {
  public:
    gl_scene(cart* _cptr, simulation *_s, int x, int y, int w, int h, const char *l = 0);
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

    bool show_node_cid, show_node_lid, show_node_mark;
    bool show_poly_cid, show_poly_lid;
    bool show_grid, show_grid_mark;
    bool show_pawn_mark;
    bool animate_pawns;
    int view_mode;
    bool show_attractions, show_sources, show_barriers, show_polygons;
    unsigned long long int frame_number;
    std::map<std::string, int> type2color;

    std::vector<std::vector<std::vector<pawn>>> pawn_history; // pawn_history[time_idx][type][idx]
    int pawn_idx;

    simulation *s;

    // draw whole scene
    void draw_scene();
    void draw_cart();
    void draw_node_cid();
    void draw_node_lid();
    void draw_node_mark();
    void draw_poly_cid();
    void draw_poly_lid();
    void draw_grid();
    void draw_grid_mark();
    void draw_pawn_mark();
    void draw_attractions();
    void draw_sources();
    void draw_barriers();
    void draw_polygons();

    // draw basic object
    template<typename... Args> void draw(const Args &...args);
  };
};
