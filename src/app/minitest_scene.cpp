#include <minitest_gui.h>

#include <color_palette.hpp>

extern Fl_Value_Slider *zoom_slider;
extern Fl_Text_Display *info_box;
extern Fl_Text_Buffer *text_buff;
extern Fl_Input *select_input;
extern gui::gl_scene *scene;

constexpr double VIEW_BLANK_BOUNDARY_FACTOR = 1.2;
// constexpr double SCROLL_TO_ZOOM = 0.125;
constexpr double SCROLL_TO_ZOOM = 0.5;

#define set_color_flux_FT glColor3d(106.f/255.f, 144.f/255.f, 200.f/255.f);
#define set_color_flux_TF glColor3d(35.f/255.f, 230.f/255.f, 200.f/255.f);

gui::gl_scene::gl_scene(cart* _c, int x, int y, int w, int h, const char *l) :
Fl_Gl_Window(x, y, w, h, l),
reDraw(true),
dijkstra_status(-2),
show_node_cid(false), show_node_lid(false), show_node_mark(true),
show_poly_cid(false), show_poly_lid(false),
show_subgraph(false), show_select(false),
show_arc_mark(false), show_pointproj_mark(false),
show_grid(false), show_grid_mark(false), show_dijkstra(true),
show_polyinsquare_mark(false), show_polyusage(false),
enable_animation(false), view_mode(MENU_VIEW_SIMPLE)
{
  c = _c;
  zoom_val = 1.0;
  ilatshift = 0;
  ilonshift = 0;
  ilatorig = 0;
  ilonorig = 0;

  // time
  bitpattTF = 0xFF; //0x3C0;    // looks like 0000001111000000 ______^^^^______
  bitpattFT = 0xFF; //0x3C0;    // looks like 0000001111000000 ______^^^^______
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
}

////////////////////////////////////////////////////////////////////////////////////////////////////
////////////// DRAW BASIC OBJECT
////////////////////////////////////////////////////////////////////////////////////////////////////

template<>
void gui::gl_scene::draw(const int &x, const int &y, const int &w, const int &h, const int &r, const int &g, const int &b, const double &z)
{
  glPushMatrix();
  glBegin(GL_QUADS);
  glColor3d(r/255.f, g/255.f, b/255.f);
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

void gui::gl_scene::draw_line(const point_base &pt1, const point_base &pt2)
{
  draw(pt1.ilon, pt1.ilat, pt2.ilon, pt2.ilat);
}

template<>
void gui::gl_scene::draw(const arc_base &a)
{
  draw_line(*a.ptF, *a.ptT);
}

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
  draw_line(path.ptstart, endp);
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
  draw_line(path.ptend, endp);
  for(int i=0; i<(int)path.ptend.a->p->arc.size(); ++i)
    if(dynamic_comp(path.ptend.a->p->arc[i]->lid, path.ptend.a->lid, is_less))
      draw(*path.ptend.a->p->arc[i]);

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
    case MENU_VIEW_LVLPS:
      colormap(p.lvl_ps, 60., 210.);
      break;
    case MENU_VIEW_SIMPLE:
    default:
      switch(p.oneway)
      {
        case ONEWAY_BOTH:   glColor3d(0.4, 0.4, 0.4); break;
        case ONEWAY_TF:     glColor3d(0.0, 0.0, 1.0); break;
        case ONEWAY_FT:     glColor3d(79.f/255.f, 176.f/255.f, 0.f/255.f); break;
        case ONEWAY_CLOSED: glColor3d(255.f/255.f, 47.f/255.f, 146.f/255.f); break;
        //case ONEWAY_CLOSED: glColor3d(0.f/255.f, 191.f/255.f, 255.f/255.f); break; // blue for dark background
        default:            glColor3d(0.0, 0.0, 0.0); break;
      }
      //uncomment to diversify color for speed
      //if (p.speed <= 40.0/3.6) glColor3d(0.0, 0.8, 0.8);
      //else if (p.speed <= 70.0 / 3.6) glColor3d(0.3, 0.3, 0.8);
      //else if (p.speed <= 100.0 / 3.6) glColor3d(1.0, 0.55, 0.1);
      //else glColor3d(1.0, 0.0, 0.0);

      break;

    }
    draw(p);
  }

  if ( view_mode == MENU_VIEW_LVLPS )
  {
    float size = 50.0;
    for (int i = 0; i < CMAP_LEN; ++i)
    {
      draw(ilonmin + int( i * size * loneps),
           ilatmin - int( size * lateps),
           int(size * loneps), int(size * lateps),
           int(rgb_cmap[i*3 + 0]*255), int(rgb_cmap[i*3 + 1]*255), int(rgb_cmap[i*3 + 2]*255),
           0.);
    }
  }

  glPopMatrix();
}

// dijkstra path
void gui::gl_scene::draw_dijkstra()
{
  glPushMatrix();
  glLineWidth(5.);
  // node to node dijkstra
  for(int i=0; i < (int)dijkstra_node.size(); ++i)
  {
    color_palette(i);
    for(const auto &p : dijkstra_node[i].poly) draw(*p);
  }
  // point to point dijkstra
  for(int i=0; i < (int)dijkstra_point.size(); ++i)
  {
    color_palette(i);
    draw(dijkstra_point[i]);
  }
  glPopMatrix();
}

// node and point
void gui::gl_scene::draw_node_mark()
{
  //float size = 10.0;
  // float size = 2.5;
  float size = 1;
  for (const auto &n : c->node)
    draw(n.ilon - int(0.5 * size * loneps),
         n.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         0, 0, 255,
         0.);

  //size = 20.0;
  size = 5.0;
  for(const auto &n1 : currentn1)
    if(n1 != c->node.end())
      draw(n1->ilon - int(0.5 * size * loneps),
           n1->ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           0, 255, 77,
           0.);

  for(const auto &n2 : currentn2)
    if(n2 != c->node.end())
      draw(n2->ilon - int(0.5 * size * loneps),
           n2->ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           255, 0, 128,
           0.);
}

void gui::gl_scene::draw_pointproj()
{
  float size = 0.5;
  for(const auto &pt1 : currentpt1)
    draw(pt1.ilon - int(0.5 * size * loneps),
         pt1.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         0, 155, 10,
         0.5);

  for(const auto &proj1 : currentptproj1)
    draw(proj1.ilon - int(0.5 * size * loneps),
         proj1.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         0, 155, 10,
         0.5);

  for(const auto &pt2 : currentpt2)
    draw(pt2.ilon - int(0.5 * size * loneps),
         pt2.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         0, 10, 155,
         0.5);

  for(const auto &proj2 : currentptproj2)
    draw(proj2.ilon - int(0.5 * size * loneps),
         proj2.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         0, 10, 155,
         0.5);

  for(const auto &ptv : currentptv)
    draw(ptv.ilon - int(0.5 * size * loneps),
         ptv.ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         240, 10, 25,
         0.5);
}

template<>
void gui::gl_scene::draw(const poly_it &poly, const int &xshift, const int &yshift, const unsigned short &bitpatt)
{
  glPushMatrix();
  glPushAttrib(GL_ENABLE_BIT);
  glLineWidth(4.);
  glTranslated(xshift, yshift, 0);
  glLineStipple(4, bitpatt);
  glEnable(GL_LINE_STIPPLE);
  glBegin(GL_LINES);
  for(auto a : poly->arc)
  {
    glVertex3d(GLdouble(a->ptF->ilon - iloncen), GLdouble(a->ptF->ilat - ilatcen), 0.);
    glVertex3d(GLdouble(a->ptT->ilon - iloncen), GLdouble(a->ptT->ilat - ilatcen), 0.);
  }
  glEnd();
  glPopAttrib();
  glPopMatrix();
}

// arc
void gui::gl_scene::draw_link_mark()
{
  if( currenta != c->arc.end() )
  {
    glPushMatrix();
    glLineWidth(4.);
    glColor3d(255.f/255.f, 144.f/255.f, 0.f/255.f);
    draw(*currenta);
    glPopMatrix();
  }

  for(const auto p : currentpoly)
    if( p != c->poly.end() )
    {
      double dlat = double(p->nT->ilat - p->nF->ilat);
      double dlon = double(p->nT->ilon - p->nF->ilon);
      double norm = std::sqrt(dlat*dlat + dlon*dlon);
      dlat /= norm; dlon /= norm;
      int shift = 30;

      set_color_flux_FT;
      draw(p, int(shift*dlat), int(-shift*dlon), scene->bitpattFT);
      set_color_flux_TF;
      draw(p, int(-shift*dlat), int(shift*dlon), scene->bitpattTF);
    }
}

// grid
void gui::gl_scene::draw_grid_mark()
{
  draw(c->grid[mouserow][mousecol].ilonleft,
       c->grid[mouserow][mousecol].ilatbot,
       c->grid.gdlon, c->grid.gdlat,
       0, 0, 0,
       0.0);
}

void gui::gl_scene::draw_grid()
{
  glLineWidth(1.);
  glColor3d(0.2f, 0.2f, 0.2f);
  for (const auto &row : c->grid)
  {
    draw(c->grid.gilonmin, row.front().ilatbot,
         c->grid.gilonmax, row.front().ilatbot );
  }
  for(const auto &col : c->grid.front())
    draw(col.ilonleft, c->grid.gilatmin,
         col.ilonleft, c->grid.gilatmax);
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

void gui::gl_scene::draw_subgraph()
{
  glPushMatrix();
  for (const auto &p : c->poly)
  {
    glLineWidth(10.);
    if ( c->node_subgra[p.nT->lid] == c->node_subgra[p.nF->lid] && p.oneway != ONEWAY_CLOSED )
    {
      int coloridx = ( 255 * c->node_subgra[p.nT->lid]) / int(c->subgraph.size()) + 100;
      color_palette(coloridx);
      draw(p);
    }
  }

  float size = 10.0;
  for (const auto &n : c->subgraph[-1])
  {
    draw(c->node[n].ilon - int(0.5 * size * loneps),
         c->node[n].ilat - int(0.5 * size * lateps),
         int(size * loneps), int(size * lateps),
         255, 255, 255,
         0.);
  }
  glPopMatrix();
}

void gui::gl_scene::draw_select()
{
  std::string selected = select_input->value();
  //std::cout << "INPUT " << selected << std::endl;

  if ( selected.size() == 0 )
  {
    return;
  }
  else if (selected[0] == 'n' || selected[0] == 'N' )
  {
    try
    {
      int n = std::stoi(selected.substr(1));
      float size = 20.0;
      // float size = 30.0;
      // float size = 1;

      draw(c->node.at(n).ilon - int(0.5 * size * loneps),
           c->node.at(n).ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           255, 0, 0,
           0.);
    }
    catch(...)
    {
      std::cout << "Invalid node inserted : " << selected << std::endl;
    }
  }
  else if (selected[0] == 'p' || selected[0] == 'P')
  {
    try
    {
      float size = 20.0;
      int p = std::stoi(selected.substr(1));
      glLineWidth(5.);
      glColor3d(1.f, 0.f, 0.f);
      draw(c->poly.at(p));
      auto nF = c->poly.at(p).nF;
      draw(nF->ilon - int(0.5 * size * loneps),
           nF->ilat - int(0.5 * size * lateps),
           int(size * loneps), int(size * lateps),
           0, 255, 0,
           0.);

    }
    catch (...)
    {
      std::cout << "Invalid node inserted : " << selected << std::endl;
    }
  }
  else if (selected[0] == 'c')
  {
    try
    {
      int n = c->get_node_cid(std::stoul(selected.substr(1)))->lid;
      float size = 10.0;
      draw(c->node.at(n).ilon - int(0.5 * size * loneps),
        c->node.at(n).ilat - int(0.5 * size * lateps),
        int(size * loneps), int(size * lateps),
        255, 0, 0,
        0.);
    }
    catch (...)
    {
      std::cout << "Invalid node cid inserted : " << selected << std::endl;
    }
  }
  else if (selected[0] == 'C')
  {
    try
    {
      int p = c->get_poly_cid(std::stoul(selected.substr(1)))->lid;
      glLineWidth(5.);
      glColor3d(0.f, 0.f, 1.f);
      draw(c->poly.at(p));
    }
    catch (...)
    {
      std::cout << "Invalid poly cid inserted : " << selected << std::endl;
    }
  }
}

void gui::gl_scene::draw_poly_insquare()
{
  if (!c->is_in_bbox(mousept)) return;
  std::list<unsigned long long> poly = c->get_poly_insquare(mousept.ilat, mousept.ilon, 100.0);
  glColor3d(1.0, 0.0, 0.0);
  glLineWidth(1.0);
  for (const auto &p : poly)
  {
    glBegin(GL_LINE_STRIP);
    for (const auto &pt : c->get_poly_cid(p)->point)
      glVertex3d(GLdouble(pt->ilon - iloncen), GLdouble(pt->ilat - ilatcen), 0.3);
    glEnd();
  }
}

void gui::gl_scene::draw_poly_usage()
{
  for(int i=0; i<(int)c->poly_usage.size(); ++i)
  {
    int cnt = c->poly_usage[i];
    if( cnt >= 500 && cnt < 800 )       { glLineWidth(3.0); glColor3d(1.0, 1.0, 0.2); }
    else if( cnt >= 800 && cnt < 1700 ) { glLineWidth(3.0); glColor3d(1.0, 0.7, 0.0); }
    else if( cnt >= 1700 )              { glLineWidth(3.0); glColor3d(1.0, 0.0, 0.2); }
    else                                { glLineWidth(1.0); glColor3d(0.4, 0.4, 0.4); }
    draw(c->poly[i]);
  }
}

// draw scene
void gui::gl_scene::draw_scene()
{
  ++frame_number;
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
  glPushMatrix();
  glScaled(zoom_val, zoom_val, 1);
  glTranslated(ilonshift, ilatshift, 0);
  draw_cart();
  if (show_node_cid)          draw_node_cid();
  if (show_node_lid)          draw_node_lid();
  if (show_node_mark)         draw_node_mark();
  if (show_poly_cid)          draw_poly_cid();
  if (show_poly_lid)          draw_poly_lid();
  if (show_subgraph)          draw_subgraph();
  if (show_select)            draw_select();
  if (show_grid)              draw_grid();
  if (show_grid_mark)         draw_grid_mark();
  if (show_arc_mark)          draw_link_mark();
  if (show_dijkstra)          draw_dijkstra();
  if (show_pointproj_mark)    draw_pointproj();
  if (show_polyinsquare_mark) draw_poly_insquare();
  if (show_polyusage)         draw_poly_usage();
  glPopMatrix();
}

void gui::gl_scene::draw()
{
  if (!valid())
  {
    glClearColor(242.f / 255, 230.f / 255, 196.f / 255, 1.0f);   // Set background color : giallino
    //glClearColor(0.f / 255, 0.f / 255, 0.f / 255, 1.0f);           // Set background color : nero
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
  std::stringstream infoss;
  infoss << "Coords           : " << mousept.ilat << " " << mousept.ilon << std::endl
         << "Grid cell        : " << mouserow << ", " << mousecol << std::endl
         << "Cell Node num    : " << c->grid[mouserow][mousecol].node.size() << std::endl
         << "Cell Arc num     : " << c->grid(mousept).arc.size() << std::endl
         << "Nearest poly     : " << ((nearest_p != c->poly.end()) ? std::to_string(nearest_p->lid) : std::string("none")) << " (" << ((nearest_p != c->poly.end()) ? std::to_string(nearest_p->cid) : std::string("none")) << ")" << std::endl
         << "Nearest arc      : " << ((nearest_a != c->arc.end()) ? std::to_string(nearest_a->lid) : std::string("none")) << std::endl
         << "Nearest node     : " << ((nearest_n != c->node.end()) ? std::to_string(nearest_n->lid) : std::string("none")) << " (" << ((nearest_n != c->node.end()) ? std::to_string(nearest_n->cid) : std::string("none")) << ")" << std::endl
         << "Current poly     : " << ((currentpoly.size() && currentpoly.back() != c->poly.end()) ? std::to_string(currentpoly.back()->lid) : std::string("none")) << " (" << ((currentpoly.size() && currentpoly.back() != c->poly.end()) ? std::to_string(currentpoly.back()->cid) : std::string("none")) << ")" << std::endl
         << "Current arc      : " << ((currenta != c->arc.end()) ? std::to_string(currenta->lid) : std::string("none")) << std::endl
         << "Current node 1   : " << ((currentn1.size() && currentn1.back() != c->node.end()) ? std::to_string(currentn1.back()->lid) : std::string("none")) << std::endl
         << "Current node 2   : " << ((currentn2.size() && currentn2.back() != c->node.end()) ? std::to_string(currentn2.back()->lid) : std::string("none")) << std::endl
         << "Current point 1  : " << ((currentpt1.size()) ? std::to_string(currentpt1.back().ilat) + " " + std::to_string(currentpt1.back().ilon) : std::string("none")) << std::endl
         << "Current point 2  : " << ((currentpt2.size()) ? std::to_string(currentpt2.back().ilat) + " " + std::to_string(currentpt2.back().ilon) : std::string("none")) << std::endl
         << "Path node-node   : " << dijkstra_node.size() << std::endl
         << "Path point-point : " << dijkstra_point.size() << std::endl
         << "Frame number     : " << frame_number << std::endl;
  text_buff->text(infoss.str().c_str());
  info_box->buffer(text_buff);
}

int gui::gl_scene::handle(int event)
{
  switch (event)
  {
  case FL_PUSH:
    screen_to_coord(ilatorig, ilonorig);
    ilatorig -= ilatshift;
    ilonorig -= ilonshift;
    switch (Fl::event_button())
    {
    case FL_LEFT_MOUSE:
      if( Fl::event_ctrl() )
      {
        currentn1.push_back(c->get_nearest_node(mousept));
      }
      else if ( Fl::event_alt() )
      {
        currentn2.push_back(c->get_nearest_node(mousept));
        if( currentn1.size() && currentn1.back() != c->node.end() &&
            currentn2.size() && currentn2.back() != c->node.end() &&
            currentn2.back() != currentn1.back() )
          dijkstra_status = c->bestpath(currentn1.back(), currentn2.back(), dijkstra_node);
          
      }
      else
      {
        if( mousept != point_base() )
        {
          auto ca = c->get_nearest_arc(mousept);
          if( ca != c->arc.end() ) currentpoly.push_back(ca->p);
        }
      }
      break;
    case FL_RIGHT_MOUSE:
      if ( Fl::event_ctrl() && !Fl::event_shift() )     // ctrl-right click
      {
        currentpt1.push_back(mousept);
        currentptproj1.push_back(c->project(currentpt1.back(), c->get_nearest_arc(currentpt1.back())));
      }
      else if ( Fl::event_alt() )                       // alt-right click
      {
        currentpt2.push_back(mousept);
        currentptproj2.push_back(c->project(currentpt2.back(), c->get_nearest_arc(currentpt2.back())));
        if( currentpt1.size() && currentpt2.size() )
          dijkstra_status = c->bestpath(currentpt1.back(), currentpt2.back(), dijkstra_point);
      }
      else if ( Fl::event_shift() && !Fl::event_ctrl() )  // shift-right click
      {
        currentptv.push_back(mousept);
      }
      else if ( Fl::event_shift() && Fl::event_ctrl() )   // ctrl-shift-right click
      {
        currentptv.push_back(mousept);
        if( currentptv.size() ) dijkstra_status = c->bestpath(currentptv, dijkstra_point);
      }
      else                                                // right click
      {
        currenta = c->get_nearest_arc(mousept);
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
    zoom_slider->value(zoom_val);
    reDraw = true;
    break;
  case FL_MOVE:
  {
    screen_to_coord(mousept);
    mousept.ilat -= ilatshift;
    mousept.ilon -= ilonshift;
    update_infobox();
    reDraw = true;
    break;
  }
  default:
    return Fl_Gl_Window::handle(event);
  }
  return 1;
}
