#include <vici_gui.h>
#include <color_palette.hpp>

extern Fl_Value_Slider *zoom_slider;
extern Fl_Text_Display *info_box;
extern Fl_Text_Buffer *text_buff;
extern Fl_Button *animation_button, *forward_button, *backward_button, *reset_button;
extern gui::gl_scene *scene;

constexpr double VIEW_BLANK_BOUNDARY_FACTOR = 1.2;
constexpr double SCROLL_TO_ZOOM = 0.125;


#define set_color_flux_FT glColor3d(106.f/255.f, 144.f/255.f, 200.f/255.f);
#define set_color_flux_TF glColor3d(35.f/255.f, 230.f/255.f, 200.f/255.f);

gui::gl_scene::gl_scene(cart* _c, simulation *_s, int x, int y, int w, int h, const char *l) :
Fl_Gl_Window(x, y, w, h, l),
c(_c),
ilatshift(0), ilonshift(0), ilatorig(0), ilonorig(0),
reDraw(true),
show_node_cid(false), show_node_lid(false), show_node_mark(true),
show_poly_cid(false), show_poly_lid(false),
show_grid(false), show_grid_mark(false),
show_pawn_mark(true),
animate_pawns(false), view_mode(MENU_VIEW_SIMPLE),
show_attractions(true), show_sources(false), show_barriers(false), show_polygons(false),
pawn_idx(0),
s(_s)
{
  zoom_val = 1.0;

  // time
  frame_number = 0;

  // local coordinate geometry
  ilatmin = c->ilat_min;
  ilatmax = c->ilat_max;
  ilonmin = c->ilon_min;
  ilonmax = c->ilon_max;
  iloncen = int(0.5 * (ilonmax + ilonmin));
  ilatcen = int(0.5 * (ilatmax + ilatmin));
  dilat = int(0.5 * (ilatmax - ilatmin) * VIEW_BLANK_BOUNDARY_FACTOR);
  dilon = int(0.5 * (ilonmax - ilonmin) * VIEW_BLANK_BOUNDARY_FACTOR);
  lateps = dilat / 1000;
  loneps = ( lateps * this->w() ) / this->h();
  mousept = point_base();
  currenta = c->arc.end();

  // pawn tag to color index map
  int i = 0;
  for (const auto &pt : s->pawn_types)
  {
    std::string tag = pt.first;
    type2color[tag] = i++ * CMAP_LEN / int(s->pawn_types.size());
    type2color[tag] = type2color[tag] == 0 ? 1 : type2color[tag]; // 0-index colormap is black
  }
}

////////////////////////////////////////////////////////////////////////////////////////////////////
////////////// DRAW BASIC OBJECT
////////////////////////////////////////////////////////////////////////////////////////////////////

template<>
void gui::gl_scene::draw(const int &x, const int &y, const int &w, const int &h, const double &z)
{
  glPushMatrix();
  glBegin(GL_QUADS);
  glVertex3d(GLdouble(x - iloncen),     GLdouble(y - ilatcen)    , GLdouble(z));
  glVertex3d(GLdouble(x + w - iloncen), GLdouble(y - ilatcen)    , GLdouble(z));
  glVertex3d(GLdouble(x + w - iloncen), GLdouble(y + h - ilatcen), GLdouble(z));
  glVertex3d(GLdouble(x - iloncen),     GLdouble(y + h - ilatcen), GLdouble(z));
  glEnd();
  glPopMatrix();
}

template<>
void gui::gl_scene::draw(const int &x1, const int &y1, const int &x2, const int &y2)
{
  glBegin(GL_LINE_STRIP);
  glVertex3d(GLdouble(x1 - iloncen), GLdouble(y1 - ilatcen), 0.);
  glVertex3d(GLdouble(x2 - iloncen), GLdouble(y2 - ilatcen), 0.);
  glEnd();
}

template <> void gui::gl_scene::draw(const point_base &pt1, const point_base &pt2) { draw(pt1.ilon, pt1.ilat, pt2.ilon, pt2.ilat); }
template <> void gui::gl_scene::draw(const point_proj &pt1, const point_base &pt2) { draw(pt1.ilon, pt1.ilat, pt2.ilon, pt2.ilat); }
template <> void gui::gl_scene::draw(const arc_base &a) { draw(*a.ptF, *a.ptT); }

template<>
void gui::gl_scene::draw(const poly_base &p)
{
  glBegin(GL_LINE_STRIP);
  for (const auto &pt : p.point) glVertex3d(GLdouble(pt->ilon - iloncen), GLdouble(pt->ilat - ilatcen), 0.);
  glEnd();
}

template<>
void gui::gl_scene::draw(const path_point &path)
{
  auto dynamic_comp = [](const int &a, const int &b, const bool &is_less )
  {
    if (is_less) return a < b;
    else return a > b;
  };

  // first poly chunk
  point_base endp;
  bool is_less = true;
  if (path.ptstart.a->p->nF == path.poly.front()->nF || path.ptstart.a->p->nF == path.poly.front()->nT)
  {
    endp = *path.ptstart.a->ptF;
    is_less = true;
  }
  else if (path.ptstart.a->p->nT == path.poly.front()->nF || path.ptstart.a->p->nT == path.poly.front()->nT)
  {
    endp = *path.ptstart.a->ptT;
    is_less = false;
  }
  else { std::cerr << "You are not supposed to read this...." << std::endl; }
  draw(path.ptstart, endp);
  for (int i = 0; i<(int)path.ptstart.a->p->arc.size(); ++i)
    if( dynamic_comp(path.ptstart.a->p->arc[i]->lid, path.ptstart.a->lid, is_less) )
      draw(*path.ptstart.a->p->arc[i]);

  // internal poly
  for(const auto &p : path.poly) draw(*p);

  // last poly chunk
  if ( path.ptend.a->p->nF == path.poly.back()->nF || path.ptend.a->p->nF == path.poly.back()->nT )
  {
    endp = *path.ptend.a->ptF;
    is_less = true;
  }
  else if ( path.ptend.a->p->nT == path.poly.back()->nF || path.ptend.a->p->nT == path.poly.back()->nT )
  {
    endp = *path.ptend.a->ptT;
    is_less = false;
  }
  else { std::cerr << "You are not supposed to read this...." << std::endl; }
  draw(path.ptend, endp);
  for(int i=0; i<(int)path.ptend.a->p->arc.size(); ++i)
    if(dynamic_comp(path.ptend.a->p->arc[i]->lid, path.ptend.a->lid, is_less))
      draw(*path.ptend.a->p->arc[i]);

}

template <>
void gui::gl_scene::draw(const poly_it &poly, const int &xshift, const int &yshift, const unsigned short &bitpatt)
{
  glPushMatrix();
  glPushAttrib(GL_ENABLE_BIT);
  glLineWidth(4.);
  glTranslated(xshift, yshift, 0);
  glLineStipple(4, bitpatt);
  glEnable(GL_LINE_STIPPLE);
  glBegin(GL_LINES);
  for (auto a : poly->arc)
  {
    glVertex3d(GLdouble(a->ptF->ilon - iloncen), GLdouble(a->ptF->ilat - ilatcen), 0.);
    glVertex3d(GLdouble(a->ptT->ilon - iloncen), GLdouble(a->ptT->ilat - ilatcen), 0.);
  }
  glEnd();
  glPopAttrib();
  glPopMatrix();
}

////////////////////////////////////////////////////////////////////////////////////////////////////
////////////// DRAW SCENE COMPONENTS
////////////////////////////////////////////////////////////////////////////////////////////////////

// draw carthography
void gui::gl_scene::draw_cart()
{
  glPushMatrix();
  for (const auto &p : c->poly)
  {
    glLineWidth(1.);
    switch (view_mode)
    {
      case MENU_VIEW_LVLPS_CLOSED:
      {
        if (s->lvlps_tt.size())
        {
          int ts = pawn_idx * s->sampling_dt + s->start_time;
          int time_idx = ((ts - s->midn_t_start) * int(s->lvlps_tt.size()) ) / (s->midn_t_stop - s->midn_t_start);
          if ( p.lvl_ps > s->lvlps_tt[time_idx] )
            glColor3d(0.4, 0.4, 0.4);
          else
            glColor3d(255.f/255.f, 47.f/255.f, 146.f/255.f);
        }
        else
          glColor3d(0.4, 0.4, 0.4);
        break;
      }
      case MENU_VIEW_LVLPS_CMAP:
      {
        colormap(p.lvl_ps, 60., 210.);
        break;
      }
      case MENU_VIEW_SIMPLE:
      default:
      {
        switch(p.oneway)
        {
          case ONEWAY_BOTH:   glColor3d(0.4, 0.4, 0.4); break;
          case ONEWAY_TF:     glColor3d(0.0, 0.0, 1.0); break;
          case ONEWAY_FT:     glColor3d(79.f/255.f, 176.f/255.f, 0.f/255.f); break;
          case ONEWAY_CLOSED: glColor3d(255.f/255.f, 47.f/255.f, 146.f/255.f); break;
          default:            glColor3d(0.0, 0.0, 0.0); break;
        }
        break;
      }
    }
    draw(p);
  }

  if ( view_mode == MENU_VIEW_LVLPS_CMAP )
  {
    float size = 50.0;
    for (int i = 0; i < CMAP_LEN; ++i)
    {
      colormap(i, 0., CMAP_LEN-1.);
      draw(ilonmin + int( i * size * loneps),
           ilatmin - int( size * lateps),
           int(size * loneps), int(size * lateps),
           0.);
    }
  }
  glPopMatrix();

  // datetime
  if (false)
  {
    glDisable(GL_DEPTH_TEST);
    gl_font(FL_TIMES, 20);
    color_palette(BLACK);
    std::string datetime = "Venezia " + physycom::unix_to_date(s->start_time + s->sampling_dt * pawn_idx);
    gl_draw(datetime.c_str(), int(-0.5*dilon), int(-0.8*dilat));
    glEnable(GL_DEPTH_TEST);
  }
}

// node and point
void gui::gl_scene::draw_node_mark()
{
  float size = 1.0;

  color_palette(BLUE);
  for (const auto &n : c->node)
    if (!n.stops)
    {
      draw(n.ilon - int(0.5 * size * loneps),
           n.ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           0.);
    }
    else
    {
      draw(n.ilon - int(0.5 * size * loneps),
           n.ilat - int(0.5 * size * lateps),
           int(2.0 * loneps), int(2.0 * lateps),
           0.);
    }
}

// grid
void gui::gl_scene::draw_grid_mark()
{
  color_palette(BLACK);
  draw(c->grid[mouserow][mousecol].ilonleft,
       c->grid[mouserow][mousecol].ilatbot,
       c->grid.gdlon, c->grid.gdlat,
       0.0);
}

void gui::gl_scene::draw_grid()
{
  glLineWidth(1.);
  color_palette(GREY);
  for (const auto &row : c->grid)
    draw(c->grid.gilonmin, row.front().ilatbot, c->grid.gilonmax, row.front().ilatbot );
  for(const auto &col : c->grid.front())
    draw(col.ilonleft, c->grid.gilatmin, col.ilonleft, c->grid.gilatmax);
}

// labels
void gui::gl_scene::draw_node_cid()
{
  glDisable(GL_DEPTH_TEST);
  gl_font(FL_HELVETICA, 10);
  glColor3d(0.0, 0.0, 0.0);
  for (const auto &n : c->node)
  {
    std::string cid = std::to_string(n.cid);
    gl_draw(cid.c_str(), n.ilon - iloncen, n.ilat - ilatcen);
  }
  glEnable(GL_DEPTH_TEST);
}

void gui::gl_scene::draw_node_lid()
{
  glDisable(GL_DEPTH_TEST);
  gl_font(FL_HELVETICA, 10);
  glColor3d(0.0, 0.0, 0.0);
  for (const auto &n : c->node)
  {
    std::string lid = std::to_string(n.lid);
    gl_draw(lid.c_str(), n.ilon - iloncen, n.ilat - ilatcen);
  }
  glEnable(GL_DEPTH_TEST);
}

void gui::gl_scene::draw_poly_cid()
{
  glDisable(GL_DEPTH_TEST);
  gl_font(FL_HELVETICA, 10);
  glColor3d(0.0, 0.0, 0.0);
  for (const auto &p : c->poly)
  {
    std::string cid = std::to_string(p.cid);
    int llat = (p.point.front()->ilat + p.point.back()->ilat) / 2;
    int llon = (p.point.front()->ilon + p.point.back()->ilon) / 2;
    gl_draw(cid.c_str(), llon - iloncen, llat - ilatcen);
  }
  glEnable(GL_DEPTH_TEST);
}

void gui::gl_scene::draw_poly_lid()
{
  glDisable(GL_DEPTH_TEST);
  gl_font(FL_HELVETICA, 10);
  glColor3d(0.0, 0.0, 0.0);
  for (const auto &p : c->poly)
  {
    std::string lid = std::to_string(p.lid);
    int llat = (p.point.front()->ilat + p.point.back()->ilat) / 2;
    int llon = (p.point.front()->ilon + p.point.back()->ilon) / 2;
    gl_draw(lid.c_str(), llon - iloncen, llat - ilatcen);
  }
  glEnable(GL_DEPTH_TEST);
}

// draw pawns
void gui::gl_scene::draw_pawn_mark()
{
  // safe pawn state access
  if (pawn_history.size() < 1) return;
  if (pawn_idx >= int(pawn_history.size()) ) pawn_idx = int(pawn_history.size() - 1);
  else if( pawn_idx < 0 ) pawn_idx = 0;
  auto pawn_state = pawn_history[pawn_idx];

  // draw pawns
  float size = 2.f;
  for (int i = 0; i < int(pawn_state.size()); ++i)
  {
    colormap(type2color[pawn_state[i].front().tag]);
    for (const auto &p : pawn_state[i])
    {
      if( p.status == PAWN_TRANSPORT )
      {
        auto p_point = point_base(c->grid.gilatmin + c->grid.gdlat, c->grid.gilonmin + c->grid.gdlon);
        draw(p_point.ilon - int(0.5 * size * loneps),
             p_point.ilat - int(0.5 * size * lateps),
             int(size * loneps), int(size * lateps),
             0.5);
      }
      else
      {
        auto p_point = c->poly[p.current_poly].get_point(p.current_s);
        draw(p_point.ilon - int(0.5 * size * loneps),
             p_point.ilat - int(0.5 * size * lateps),
             int(size * loneps), int(size * lateps),
             0.5);
      }
    }
  }
}

// draw attractions
void gui::gl_scene::draw_attractions()
{
  float size = 10.f;
  color_palette(MAGENTA);
  for (const auto &a : s->attractions)
  {
    auto node = c->node[a.node_lid];
    draw(node.ilon - int(0.5 * size * loneps),
         node.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         0.5);
    glDisable(GL_DEPTH_TEST);
    gl_font(FL_HELVETICA, 10);
    gl_draw(a.tag.c_str(), node.ilon - iloncen, node.ilat - ilatcen + int(size * loneps));
    glEnable(GL_DEPTH_TEST);
  }
}

// draw sources
void gui::gl_scene::draw_sources()
{
  float size = 10.f;
  color_palette(DARKGREEN);
  for (const auto &src : s->sources)
  {
    if (src.is_localized)
    {
      auto node = c->node[src.node_lid];
      draw(node.ilon - int(0.5 * size * loneps),
           node.ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           //0, 95, 0,
           0.5);
      glDisable(GL_DEPTH_TEST);
      gl_font(FL_HELVETICA, 10);
      gl_draw(src.tag.c_str(), node.ilon - iloncen, node.ilat - ilatcen + int(size * loneps));
      glEnable(GL_DEPTH_TEST);
    }
  }
}

// draw barriers
void gui::gl_scene::draw_barriers()
{
  float size = 100.f;
  color_palette(ORANGE);
  for (const auto &p : s->barriers)
  {
    auto b = p.second;
    if ( b.geofenced )
    {
      // draw barrier position as marker
      size = 2.f;
      draw(b.loc.ilon - int(0.5 * size * loneps),
           b.loc.ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           0.55);
      glDisable(GL_DEPTH_TEST);
      gl_font(FL_HELVETICA, 10);
      gl_draw(b.tag.c_str(),
              b.loc.ilon - iloncen,
              b.loc.ilat - ilatcen + int(size * loneps));
      glEnable(GL_DEPTH_TEST);

      // highlight associated poly
      glPushMatrix();
      glLineWidth(2.);
      draw(*(b.poly));
      glPopMatrix();

      // front of associated poly (temp)
      color_palette(MAGENTA);
      size = 4.f;
      draw(b.poly->nF->ilon - int(0.5 * size * loneps),
        b.poly->nF->ilat - int(0.5 * size * lateps),
        int(size * loneps), int(size * lateps),
        0.5);
      color_palette(ORANGE);
      

      // highlight associated node
      size = 3.f;
      draw(b.node->ilon - int(0.5 * size * loneps),
           b.node->ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           0.6);
    }
  }
}

// draw polygons
void gui::gl_scene::draw_polygons()
{
  float size = 100.f;
  color_palette(TURQUOISE);
  for (const auto &p : s->polygons)
  {
    size = 1.f;
    draw(p.centroid.ilon - int(0.5 * size * loneps),
         p.centroid.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         0.55);

    glPushMatrix();
    glBegin(GL_LINE_STRIP);
    for (const auto &pc : p.points) glVertex3d(GLdouble(pc.ilon - iloncen), GLdouble(pc.ilat - ilatcen), GLdouble(0.55));
    glEnd();
    glPopMatrix();
  }
}

// draw scene
void gui::gl_scene::draw_scene()
{
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
  glEnable(GL_BLEND);
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

  glPushMatrix();
  glScaled(zoom_val, zoom_val, 1);
  glTranslated(ilonshift, ilatshift, 0);
  draw_cart();
  if (show_node_cid)    draw_node_cid();
  if (show_node_lid)    draw_node_lid();
  if (show_node_mark)   draw_node_mark();
  if (show_poly_cid)    draw_poly_cid();
  if (show_poly_lid)    draw_poly_lid();
  if (show_grid)        draw_grid();
  if (show_grid_mark)   draw_grid_mark();
  if (show_pawn_mark)   draw_pawn_mark();
  if (show_attractions) draw_attractions();
  if (show_sources)     draw_sources();
  if (show_barriers)    draw_barriers();
  if (show_polygons)    draw_polygons();
  glPopMatrix();

  glDisable(GL_BLEND);
}

void gui::gl_scene::draw()
{
  if (!valid())
  {
    glClearColor(242.f / 255, 230.f / 255, 196.f / 255, 1.0f);     // Set background color : azzurino
    glViewport(0, 0, this->w(), this->h());                        // Make our viewport the whole window
    glMatrixMode(GL_PROJECTION);                                   // Select The Projection Matrix
    glLoadIdentity();                                              // Reset The Projection Matrix
    gluOrtho2D(-dilon, dilon, -dilat, dilat);                      // Left Right Bottom Top
    glMatrixMode(GL_MODELVIEW);                                    // Select The Modelview Matrix
    glLoadIdentity();                                              // Reset The Modelview Matrix
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);            // Clear The Screen And The Depth Buffer
    glLoadIdentity();
    // Reset The View
    glEnable(GL_DEPTH_TEST);
    valid(true);
  }
  draw_scene();
}

////////////////////////////////////////////////////////////////////////////////////////////////////
////////////// USER INTERACTION
////////////////////////////////////////////////////////////////////////////////////////////////////

void gui::gl_scene::update_infobox()
{
  c->grid.coord_to_grid(mousept.ilat, mousept.ilon, mouserow, mousecol);
  auto nearest_n = c->get_nearest_node(mousept);
  auto nearest_a = c->get_nearest_arc(mousept);
  auto nearest_p = (nearest_a != c->arc.end()) ? nearest_a->p : c->poly.end();
  int population = (pawn_history.size() == 0) ? 0 :
    std::accumulate(pawn_history[pawn_idx].begin(), pawn_history[pawn_idx].end(), 0, [](int sum, const std::vector<pawn> &p){
      return sum + (int)p.size();
    });
  std::stringstream infoss;
  infoss << "Coords           : " << mousept.ilat << " " << mousept.ilon << std::endl
         << "Grid cell        : " << mouserow << ", " << mousecol << std::endl
         << "Cell Node num    : " << c->grid[mouserow][mousecol].node.size() << std::endl
         << "Cell Arc num     : " << c->grid(mousept).arc.size()  << std::endl
         << "Nearest poly     : " << ( (nearest_p != c->poly.end())  ? std::to_string(nearest_p->lid) : std::string("none") )
                                  << " (" << ((nearest_p != c->poly.end()) ? std::to_string(nearest_p->cid) : std::string("none") ) << ") "<< std::endl
         << "Near poly lvl ps : " << ( (nearest_p != c->poly.end())  ? std::to_string(nearest_p->lvl_ps) : std::string("none") ) << std::endl
         << "Nearest node     : " << ( (nearest_n != c->node.end()) ? std::to_string(nearest_n->lid) : std::string("none") )
                                  << " (" << ( (nearest_n != c->node.end()) ? std::to_string(nearest_n->cid) : std::string("none") ) << ") " << std::endl
         << "Nearest arc      : " << ( (nearest_a != c->arc.end())  ? std::to_string(nearest_a->lid) : std::string("none") ) << std::endl
         << "Frame number     : " << frame_number << std::endl
         << "Pawn state index : " << pawn_idx << "/" << pawn_history.size() << std::endl
         << "Simulation iter  : " << s->iter << std::endl
         << "Simulation time  : " << s->start_time + s->sampling_dt * pawn_idx << std::endl
         << "Simulation date  : " << physycom::unix_to_date(s->start_time + s->sampling_dt * pawn_idx) << std::endl
         << "Population       : " << population << std::endl;
  text_buff->text(infoss.str().c_str());
  info_box->buffer(text_buff);
}

int gui::gl_scene::handle(int event)
{
  switch (event)
  {
  case FL_KEYUP:
  {
    switch (Fl::event_key())
    {
    case 32: // space bar
    case FL_Enter:
      animation_button->callback()(nullptr, nullptr);
      break;
    case FL_Right:
      forward_button->callback()(nullptr, nullptr);
      break;
    case FL_Left:
      backward_button->callback()(nullptr, nullptr);
      break;
    case 114: // 'r'
      reset_button->callback()(nullptr, nullptr);
      break;
    default:
      //std::cout << "KEYBOARD EVENT: key " << Fl::event_key() << " code " << Fl::event_text() << " check " << Fl::get_key(Fl::event_key())<< std::endl;
      break;
    }
  }
  case FL_PUSH:
    screen_to_coord(ilatorig, ilonorig);
    ilatorig -= ilatshift;
    ilonorig -= ilonshift;
    switch (Fl::event_button())
    {
    case FL_LEFT_MOUSE:
      if( Fl::event_ctrl() )
      {
        // coming soon
      }
      else if ( Fl::event_alt() )
      {
        // coming soon
      }
      else
      {
        // coming soon
      }
      break;
    case FL_RIGHT_MOUSE:
      if ( Fl::event_ctrl() && !Fl::event_shift() )     // ctrl-right click
      {
        // coming soon
      }
      else if ( Fl::event_alt() )                       // alt-right click
      {
        // coming soon
      }
      else if ( Fl::event_shift() && !Fl::event_ctrl() )  // shift-right click
      {
        // coming soon
      }
      else if ( Fl::event_shift() && Fl::event_ctrl() )   // ctrl-shift-right click
      {
        // coming soon
      }
      else                                                // right click
      {
        // coming soon
      }
      break;
    default:
      break;
    }
    break;
  case FL_DRAG:
    if ( Fl::event_button1() )
    {
      screen_to_coord(ilatshift, ilonshift);
      ilonshift -= ilonorig;
      ilatshift -= ilatorig;
      reDraw = true;
    }
    break;
  case FL_MOUSEWHEEL:
    zoom_val -= Fl::event_dy() * SCROLL_TO_ZOOM;
    zoom_val = (zoom_val < zoom_slider->minimum()) ? zoom_slider->minimum() : zoom_val;
    zoom_val = (zoom_val > zoom_slider->maximum()) ? zoom_slider->maximum() : zoom_val;
    // std::cout<<"zoom_val: "<<zoom_val<<std::endl;
    zoom_slider->value(zoom_val);
    reDraw = true;
    break;
  case FL_MOVE:
  {
    screen_to_coord(mousept);
    mousept.ilat -= ilatshift;
    mousept.ilon -= ilonshift;
    reDraw = true;
    break;
  }
  default:
    return Fl_Gl_Window::handle(event);
  }
  return 1;
}
