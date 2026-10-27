/*!
 *  \file   minitest.cpp
 *  \author A. Fabbri (alessandro.fabbri27@unibo.it), C. Mizzi (chiara.mizzi2@unibo.it)
 *  \brief  OpenGL based methods implementations for app `miniplex`.
 *  \details This file contains the implementation of the graphic method, based on the FLTK wrapper of OpenGL, realated to `miniplex` app.
 */

#include <iostream>
#include <carto.h>
#include <minitest_gui.h>
#include <physycom/histo.hpp>

using namespace std;
using namespace jsoncons;
using namespace physycom;

constexpr int MAJOR = 1;
constexpr int MINOR = 0;

#define forit(x, y) for(auto x = y.begin(); x != y.end(); ++x)
#define foritr(x, y) for(auto x = y.rbegin(); x != y.rend(); ++x)
#define each(x, y) auto x = y.rbegin(); x != y.rend(); ++x

extern gui::gl_scene *scene;

void usage(const char* progname)
{
  string pn(progname);
  cerr << "Usage: " << pn.substr(pn.find_last_of("/\\") + 1) << " path/to/json/config" << endl;
  cerr << R"(JSON CONFIG SAMPLE
{
  "file_pro"     : "roads.pro",      // poly properties input file
  "file_pnt"     : "roads.pnt",      // poly geometry input file
  "verbose"      : false,            // cartography network information and checks (stdout)
  "enable_histo" : false,            // evaluate cartography stats
  "enable_gui"   : false,            // fltk gui
  "enable_bp"    : true,             // bestpath checks
  "bp_params"    :                   // bestpath parameters
  {
    "numiter" : 1,                   // bestpath repetitions
    "n_start" : 123,                 // starting node lid
    "n_end"   : 1512,                // ending node lid
    "pt_start" :
    {
      "ilat" : 45433912,             // starting point lat
      "ilon" : 12335103              // starting point lon
    },
    "pt_end" :
    {
      "ilat" : 45434760,             // ending point lat
      "ilon" : 12337330              // ending point lon
    }
  },
  "enable_explore" : false           // enable cartography explore, from one node to the rest (long time)
}
)";
}

int main(int argc, char** argv)
{
  cout << "minitest v" << MAJOR << "." << MINOR << endl;

  string conf;
  if (argc == 2)
  {
    conf = argv[1];
  }
  else
  {
    usage(argv[0]);
    exit(1);
  }

  try
  {
    json jconf = json::parse_file(conf);

    // Init cart
    cart c(jconf);
    std::cout << c.info() << std::endl;

    if (jconf.has_member("enable_histo") && jconf["enable_histo"].as<bool>())
    {
      // Init histos
      multihisto<double> mh;
      mh.add_histo("node_degree", 0.0, 7.0, 0.5, "Node degree", "Counter", "Node Degree Distribution");
      mh.add_histo("poly_degree", 0.0, 7.0, 0.5, "Poly degree", "Counter", "Poly Degree Distribution");
      mh.add_histo("poly_len", 0.0, 200.0, 5.0, "Poly length [m]", "Counter", "Poly Length Distribution");
      mh.add_histo("poly_point_num", 2.0, 12.0, 0.5, "Poly point number", "Counter", "Poly Point Number Distribution");
      mh.add_histo("poly_arc_num", 0.0, 10.0, 1.0, "Poly arc number", "Counter", "Poly Arc Number Distribution");
      mh.add_histo("arc_len", 0.0, 100.0, 2.5, "Arc length [m]", "Counter", "Arc Length Distribution");
      mh.add_histo("grid_node_num", 0.0, 100.0, 10.0, "Node per cell", "Counter", "Grid Node Distribution");
      mh.add_histo("grid_arc_num", 0.0, 200.0, 20.0, "Arc per cell", "Counter", "Grid Arc Distribution");
      mh.add_histo("lvl_ps", 0.0, 300.0, 20, "Level PS [cm]", "Counter", "Water Level PS");

      for (const auto &n : c.node)
        mh.count("node_degree", "data", (double)n.link.size());

      for (const auto &p : c.poly)
      {
        mh.count("poly_len", "data", p.length);
        mh.count("poly_degree", "data", (double)p.poly.size());
        mh.count("poly_point_num", "data", (double)p.point.size());
        mh.count("poly_arc_num", "data", (double)p.arc.size());
        mh.count("lvl_ps", "data", (double)p.lvl_ps);
      }

      for (const auto &a : c.arc)
        mh.count("arc_len", "data", a.length);

      for (const auto &row : c.grid)
        for (const auto &cell : row)
        {
          mh.count("grid_node_num", "data", (double)cell.node.size());
          mh.count("grid_arc_num", "data", (double)cell.arc.size());
        }

      std::string histodir = jconf.has_member("histo_dir") ? jconf["histo_dir"].as<std::string>() : std::string("histo");
      mh.dump(histodir + "/");
      mh.gnuplot_cdf(histodir + "/");
    }

    c.dump_poly_geojson("carto");

    if (jconf.has_member("enable_gui") && jconf["enable_gui"].as<bool>())
    {
      // Gui
      gui g(&c);

      // Display stuff
      g.run();
    }

    if (jconf.has_member("verbose") && jconf["verbose"].as<bool>())
    {
      // Check poly
      for (const auto &poly : c.poly)
      {
        cout << "Poly " << poly.cid;
        cout << " " << poly.lid;
        cout << " (" << poly.length << " m) ";
        cout << " " << c.get_poly_cid(poly.cid)->lid;
        cout << " pt(" << poly.point.size() << ")";
        cout << " a[" << poly.arc.size() << "] ";
        cout << " - nF " << poly.nF->lid << "  nT " << poly.nT->lid;
        cout << " - poly ";
        for (const auto &linked_poly : poly.poly) cout << linked_poly->lid << " ";
        cout << endl;
      }
      cout << "-----------------------------------------------------------" << endl;

      // Check nodes
      for (const auto &node : c.node)
      {
        cout << "Node " << node.cid << " " << node.lid
          << " - linked pairs (";
        for (const auto &link : node.link)   // link = < nodeit, polyit >
        {
          string node_status;
          if (node.isF(link.second))           // with iterator
            node_status = "F";
          else if (node.isT(*link.second))     // with object
            node_status = "T";
          else
            node_status = "0";

          unsigned long long int linked_node_cid = link.first->lid;
          unsigned long long int linked_poly_cid = link.second->lid;

          cout << node_status << ","
            << linked_poly_cid << ","
            << linked_node_cid
            << ((link != *(node.link.end() - 1)) ? ") (" : "");
        }
        cout << ")" << endl;
      }

      // grid check
      int gridcnt = 0;
      for (const auto &row : c.grid)
        for (const auto &cell : row)
          cout << ++gridcnt << " -  a " << cell.arc.size() << "  n " << cell.node.size() << endl;

      // check arc
      bool arc_check = true;
      for (const auto &a : c.arc)
        if (std::distance(c.poly.begin(), a.p) < 0 || std::distance(c.poly.begin(), a.p) > int(c.poly.size() - 1)) arc_check = false;
      cout << "Arc check : " << arc_check << endl;

      // check distance
      cout << "Distance node-point : " << distance(c.node[2], c.point[3]) << endl;
      cout << "Distance arc-point  : " << distance(c.arc[0], *c.arc[0].ptT) << " " << distance(c.arc[0], *c.arc[0].ptF) << endl;
      cout << "Distance arc-point  : " << distance(c.arc[2], *c.arc[3].ptT) << " " << c.arc[3].length << " " << distance(*c.arc[2].ptT, *c.arc[3].ptT) << endl;

      // arc check reprise
      auto p = c.poly[123];
      for (const auto p : c.poly)
      {
        if (p.arc.size() < 5) continue;
        std::cout << "Poly " << p.lid << " : " << std::endl;
        for (const auto &a : p.arc) std::cout << a->lid << " " << a->p->lid << " - " << a->length << " " << a->s << " " << a->p->length << std::endl;
        break;
      }

      // subgraph check
      for (int i=0; i < int(c.node_subgra.size()); ++i)
      {
        std::cout << "Node " << i << " subg " << c.node_subgra[i] << std::endl;
      }
    }

    if (jconf.has_member("enable_bp") && jconf["enable_bp"].as<bool>())
    {
      int n_start, n_end;
      if (jconf.has_member("bp_params"))
      {
        n_start = jconf["bp_params"]["n_start"].as<int>();
        n_end = jconf["bp_params"]["n_end"].as<int>();
      }
      else
      {
        n_start = 3;
        n_end = 21;
      }

      int ret;
      node_base n1 = c.node[n_start], n2 = c.node[n_end];
      vector<pair<int, bool>> poly;  // poly_lid, orientation
      poly.reserve(jconf["bp_params"]["numiter"].as<int>());
      for (int i = 1; i < jconf["bp_params"]["numiter"].as<int>(); ++i) { ret = c.bestpath(n1, n2, poly); }
      ret = c.bestpath(n1, n2, poly); // last for maybe of 0 step
      cout << "Best path " << n_start << " - " << n_end << " : " << c.bestpath_err(ret) << endl;
      cout << "Path size : " << poly.size() << endl;
      cout << setw(6) << "poly" << setw(6) << "nodeF" << setw(6) << "nodeT" << endl;
      forit(p, poly)
      {
        cout << setw(6) << p->first
          << setw(6) << c.poly[p->first].nF->lid
          << setw(6) << c.poly[p->first].nT->lid
          << (p->second ? " FT" : " TF") << endl;
      }

      if (jconf["bp_params"].has_member("pt_start") && jconf["bp_params"].has_member("pt_end"))
      {
        point_base p1(jconf["bp_params"]["pt_start"]["ilat"].as<int>(), jconf["bp_params"]["pt_start"]["ilon"].as<int>());
        point_base p2(jconf["bp_params"]["pt_end"]["ilat"].as<int>(), jconf["bp_params"]["pt_end"]["ilon"].as<int>());
        cout << "Point1 " << p1 << endl;
        cout << "Point2 " << p2 << endl;
        vector<path_point> path;
        for (int i = 1; i < jconf["bp_params"]["numiter"].as<int>(); ++i) { ret = c.bestpath(p1, p2, path); }
        ret = c.bestpath(p1, p2, path); // last for maybe of 0 step
        cout << "Best path (x " << jconf["bp_params"]["numiter"].as<int>() << ") : " << c.bestpath_err(ret) << " " << path.back().poly.size() << endl;
        for (const auto p : path.front().poly) cout << p->lid << " ";
        cout << endl;
      }
    }

    if (jconf.has_member("enable_explore") && jconf["enable_explore"].as<bool>())
    {
      multihisto<double> mh;
      mh.add_histo("bp_return", 0.0, 5.0, 0.5);
      mh.add_histo("bp_path_len", 0.0, 5000.0, 10);
      mh.add_histo("bp_poly_num", 0.0, 150.0, 10);
      vector<path_base> path;
      int cnt = 0;

      int start_node = 123;
      auto n1 = c.node[start_node];
      string nodeid = "node " + to_string(start_node);
      int ret;
      for (const auto &n2 : c.node)
      {
        if (cnt++ % 1000 == 0) cout << "Exploring network : " << 100 * cnt++ / c.node.size() << " %      \n";
        if (n1 == n2) continue;
        ret = c.bestpath(n1, n2, path);
        mh.count("bp_return", nodeid, (double)ret);
        mh.count("bp_path_len", nodeid, path.back().length());
        mh.count("bp_poly_num", nodeid, (double)path.back().poly.size());
      }
      cout << endl;

      mh.dump(); mh.gnuplot_cdf();
    }

  }
  catch (exception &e)
  {
    cerr << "EXC: " << e.what() << endl;
    exit(1);
  }

  return 0;
}
