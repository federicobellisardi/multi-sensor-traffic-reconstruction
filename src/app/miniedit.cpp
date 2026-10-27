/*!
 *  \file   miniedit.cpp
 *  \author A. Fabbri (alessandro.fabbri27@unibo.it), C. Mizzi (chiara.mizzi2@unibo.it), S. Sinigardi (stefano.sinigardi@unibo.it)
 *  \brief  Main file for `miniedit` app.
 *  \details This file contains the source code for the app `miniedit`.
 */

#include <iostream>
#include <carto.h>
#include <minitest_gui.h>
#include <physycom/histo.hpp>
#include <physycom/string.hpp>

using namespace std;
using namespace jsoncons;
using namespace physycom;

constexpr int MAJOR = 3;
constexpr int MINOR = 5;

void usage(const char *progname)
{
  string pn(progname);
  cerr << "Usage: " << pn.substr(pn.find_last_of("/\\") + 1) << " path/to/json/config" << endl;
  cerr << R"(JSON CONFIG SAMPLE
{
  "file_pro"              : "roads.pro",
  "file_pnt"              : "roads.pnt",
  "cartout_basename"      : "roads_edit",
  "enable_merge_subgraph" : false,
  "enable_remove_degree2" : false,
  "enable_attach_nodes"   : false
}
)";
}

struct ace
{
  std::vector<point_base> points;
  double area, perimeter;
  point_base centroid;
  std::map<std::string, std::string> pro;
  int ilat_max, ilat_min, ilon_max, ilon_min;
  std::vector<node_it> node_in;
  int population;
  double score;
  ace() {};
  ace(const jsoncons::json &feature);
  int winding_number_algo(const int ilat, const int ilon);
};

ace::ace(const jsoncons::json &polygonlist)
{
  for (const auto &pt : polygonlist[0].array_range())
  {
    points.emplace_back(int(pt[1].as<double>() * 1e6), int(pt[0].as<double>() * 1e6));
  }
}

double IsLeft(const int &ilat_0, const int &ilon_0, const int &ilat_1, const int &ilon_1, const int &ilat_p, const int &ilon_p)
{
  return ((ilat_1 - ilat_0) * (ilon_p - ilon_0) - (ilat_p - ilat_0) * (ilon_1 - ilon_0));
}

int ace::winding_number_algo(const int ilat, const int ilon) {
  int wn = 0;    // the  winding number counter
  for (int i = 0; i < int(points.size()-1); ++i) // edge from polygon[i] to  polygon[i+1]
  {
    if (points[i].ilon <= ilon)
    {
      if (points[i+1].ilon > ilon)     // an upward crossing
        if (IsLeft(points[i].ilat, points[i].ilon, points[i+1].ilat, points[i+1].ilon, ilat, ilon) > 0)  // P left of  edge
          ++wn;  // have  a valid up intersect
    }
    else {                        // start y > P.y (no test needed)
      if (points[i + 1].ilon <= ilon)     // a downward crossing
        if (IsLeft(points[i].ilat, points[i].ilon, points[i + 1].ilat, points[i + 1].ilon, ilat, ilon) < 0)  // P right of  edge
          --wn; // have  a valid down intersect
    }
    //cout << "wn:  " << wn << endl;
  }

  return wn;
}

void merge_carto(cart *c1, cart c2)
{
  for (auto &p1 : c1->poly)
  {
    std::set<int> poly_match;
    std::vector<point_proj> pp_match;
    //double lenght = 0.0;
    for (auto &po1 : p1.point)
    {
      auto arc_near = c2.get_nearest_arc(po1);
      if (arc_near != c2.arc.end())
      {
        //int poly_lid = arc_near->p->lid;
        std::map<std::string, double> param;
        point_proj pp = c2.project(*po1, arc_near);
        pp_match.push_back(pp);
        poly_match.insert(arc_near->p->lid);
      }
    }

    if (pp_match.size() / p1.point.size() < 0.8) poly_match.clear();
    if (poly_match.size() != 0)
    {
      double speed = 0.0;
      for (auto &np : poly_match)
      {
        speed += c2.poly.at(np).speed;
      }
      speed /= poly_match.size();
      if (speed <=0.5)
        speed = 30.0/3.6;
      p1.speed = speed*3.6;
    }
    else{
      p1.speed = 50;
    }
  }
}

void attach_carto(cart *c1, cart c2, std::map<int, std::string> stops_list)
{
  if (stops_list.size()==0)
  {
    for (auto &n : c2.node){
      point_base p;
      p.ilat = n.ilat; p.ilon=n.ilon;
      auto nn = c1->get_nearest_node(p);
      if (nn!=c1->node.end()) {
        for (auto &np:n.link){
          if (n.isF(np.second)) np.second->nF->cid = nn->cid;
          else if (n.isT(np.second)) np.second->nT->cid = nn->cid;
        }
      }
    }
  }
  else
  {
    for (auto &n : c2.node){
      if (stops_list.find(n.cid)==stops_list.end())
        continue;
      point_base p;
      p.ilat = n.ilat; p.ilon=n.ilon;
      auto nn = c1->get_nearest_node(p);
      if (nn!=c1->node.end()) {
        for (auto &np:n.link){
          if (n.isF(np.second)) np.second->nF->cid = nn->cid;
          else if (n.isT(np.second)) np.second->nT->cid = nn->cid;
        }
      }
    }
  }
  
  std::string basename;
  basename = "carto_attached";
  std::ofstream editpro(basename + ".pro");
  std::ofstream editpnt(basename + ".pnt");
  editpro << "#poly_cid  node_front_cid  node_tail_cid  length  lvl_ps  type  width_FT  width_TF  speed  oneway  name  oneway_wheels  exclusive_FT exclusive_TF" << std::endl;

  // c1->dump_carto(editpro, editpnt);
  // c2.dump_carto(editpro, editpnt);

  editpro.close();
  editpnt.close();
}

int main(int argc, char **argv)
{
  cout << "miniedit v" << MAJOR << "." << MINOR << endl;

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
    cart* c;

    try
    {
      c = new cart(jconf);
      cout << c->info() << endl;
    }
    catch(const check_network_error& e)
    {
      std::cout<<e.what()<<std::endl;
      cerr << "Malformed network, dumping purged cartography and quitting..." << endl;
      auto cartout = jconf["cartout_basename"].as<std::string>();
      jconf["cartout_basename"] = cartout + "_bis";
      c = new cart(jconf, true);
      c->remove_doubleconnections();
      c->dump_edited();
      c->dump_edit_config(cartout);
      exit(2);
    }
    catch(const std::exception& e)
    {
      cerr << "Generic exc : " << e.what() << endl;
      exit(2);
    }

    c->update_degree();

    bool enable_merge_subgraph = jconf.has_member("enable_merge_subgraph") ? jconf["enable_merge_subgraph"].as<bool>() : false;
    if (enable_merge_subgraph)
      c->merge_subgraph();

    bool enable_remove_degree2 = jconf.has_member("enable_remove_degree2") ? jconf["enable_remove_degree2"].as<bool>() : false;
    if (enable_remove_degree2)
      c->remove_degree2();

    bool enable_attach_nodes = jconf.has_member("enable_attach_nodes") ? jconf["enable_attach_nodes"].as<bool>() : false;
    if (enable_attach_nodes)
    {
      c->attach_nodes();
      c->remove_degree2();
      c->remove_shortp();
    }

    bool enable_attach_cartos = jconf.has_member("enable_attach_cartos") ? jconf["enable_attach_cartos"].as<bool>() : false;
    if (enable_attach_cartos)
    {
      auto fname = jconf["second_carto_json"].as<std::string>();
      json jconf2 = json::parse_file(fname);
      cart c2(jconf2, true);
      std::map<int, std::string> sl;

      if (jconf.has_member("file_stops_list"))
      {
        std::ifstream stops(jconf["file_stops_list"].as<std::string>());
        if (!stops)
          throw std::runtime_error("Stops list file not found.");
        std::string line;
        std::getline(stops, line); 
        while (std::getline(stops, line))
        {
          std::vector<std::string> tok;
          std::string sep = "  ";
          physycom::split(tok, line, sep, physycom::token_compress_off);
          sl[stoi(tok[0])] = tok[1];
        }
      }
      attach_carto(c, c2, sl);
    }

    bool enable_assign_level = jconf.has_member("enable_assign_level") ? jconf["enable_assign_level"].as<bool>() : false;
    if (enable_assign_level)
      c->assign_level_ps(jconf["enable_assign_level"]["grid_file"].as<std::string>());

    if (jconf.has_member("bridge_file"))
      c->assign_level_bridge(jconf["bridge_file"].as<std::string>());

    if (jconf.has_member("enable_reduction"))
      c->reduce_area(jconf["enable_reduction"]);

    if (jconf.has_member("subgraph_removal"))
      c->remove_subgraph(jconf["subgraph_removal"]);
    
    if (jconf.has_member("enable_glue_nodes"))
    {  
      c->glue_nodes(jconf["enable_glue_nodes"].as<std::string>());
    }

    if (jconf.has_member("shadow_road"))
    {  
      c->dump_shadow_road(jconf["shadow_road"].as<std::string>());
    }    

    if (jconf.has_member("direction_road"))
    {  
      c->dump_direction_file(jconf["direction_road"].as<std::string>());
    }    

    if (jconf.has_member("enable_merge_carto")) {
      auto fname = jconf["second_carto_json"].as<std::string>();
      // std::cout<<fname<<std::endl;
      json jconf2 = json::parse_file(fname);
      cart c2(jconf2, true);
      merge_carto(c, c2);
    }

    if (jconf.has_member("enable_merge_ace")) {

      std::cout << "--- Merge ACE modality ---" << std::endl;

      std::map<std::string, ace> polygons_ace;
      int polygon_cnt = 0;

      std::ifstream ace_j(jconf["ace_geojson"].as<std::string>());
      if (!ace_j)
        throw std::runtime_error("unable to open polygons file " + jconf["ace_geojson"].as<std::string>());

      auto jpoly = jsoncons::json::parse(ace_j);

      for (const auto &feature : jpoly["features"].array_range())
      {
        if (!feature["geometry"]["coordinates"].size()) continue;
        auto type = feature["geometry"]["type"].as<std::string>();
        auto reg = feature["properties"]["REG_NAME"].as<std::string>();

        if (reg == "Emilia-Romagna")
        {
          if (type == "MultiPolygon")
          {
            //std::cout << "feature type MultiPolygon size " << feature["geometry"]["coordinates"].size() << std::endl;
            for (const auto &pol : feature["geometry"]["coordinates"].array_range())
            {
              ++polygon_cnt;
              ace aw = ace(pol);
              for (const auto &pro : feature["properties"].object_range())
                aw.pro[std::string(pro.key())] = pro.value().as<std::string>();
              string uid = aw.pro["UID"];
              aw.centroid = physycom::centroid(aw.points);
              if (polygons_ace.find(uid) == polygons_ace.end())
                polygons_ace[uid] = aw;
            }
          }
          else if (type == "Polygon")
          {
            //std::cout << "feature type Polygon size " << feature["geometry"]["coordinates"].size() << std::endl;
            ++polygon_cnt;
            auto pol = feature["geometry"]["coordinates"];
            ace aw = ace(pol);
            for (const auto &pro : feature["properties"].object_range())
              aw.pro[std::string(pro.key())] = pro.value().as<std::string>();
            string uid = aw.pro["UID"];
            aw.centroid = physycom::centroid(aw.points);
            if (polygons_ace.find(uid) == polygons_ace.end())
              polygons_ace[uid] = aw;
          }
          else
          {
            std::cerr << "GEOJSON feature type " << type << " unsupported" << std::endl;
          }
        }
      }

      std::cout << "num ace        : " << polygons_ace.size() << std::endl;

      // read popultion properties
      std::ifstream ace_pop(jconf["population_file"].as<std::string>());
      if (!ace_pop)
        throw std::runtime_error("unable to open polygons file " + jconf["population_file"].as<std::string>());

      std::string line;
      std::getline(ace_pop, line); // skip header

      int population_total = 0;
      while (std::getline(ace_pop, line))
      {
        std::vector<std::string> tok;
        std::string sep = ";";
        physycom::split(tok, line, sep, physycom::token_compress_off);
        if (polygons_ace.find(tok[0]) != polygons_ace.end()) {
          polygons_ace[tok[0]].population = stoi(tok[1]);
          population_total += stoi(tok[1]);
        }
      }

      std::cout << "totale pop     : " << population_total << std::endl;

      // find intersection ace-nodes
      for (auto &pga : polygons_ace)
      {
        //assign relative score
        pga.second.score = (pga.second.population*1e4) / (float)population_total;
        std::set<node_it> node_closest;
        pga.second.ilat_max = 0;
        pga.second.ilat_min = c->ilat_max;
        pga.second.ilon_max = 0;
        pga.second.ilon_min = c->ilon_max;

        for (const auto &cord : pga.second.points) {
          if (cord.ilat > pga.second.ilat_max) pga.second.ilat_max = cord.ilat;
          if (cord.ilat < pga.second.ilat_min) pga.second.ilat_min = cord.ilat;
          if (cord.ilon > pga.second.ilon_max) pga.second.ilon_max = cord.ilon;
          if (cord.ilon < pga.second.ilon_min) pga.second.ilon_min = cord.ilon;
        }
        int row_max, col_max;
        int row_min, col_min;
        c->grid.coord_to_grid(pga.second.ilat_max, pga.second.ilon_max, row_max, col_max);
        c->grid.coord_to_grid(pga.second.ilat_min, pga.second.ilon_min, row_min, col_min);

        for (int rw = row_min; rw < row_max; ++rw)
        {
          for (int cl = col_min; cl < col_max; ++cl)
          {
            for (const auto &n : c->grid.grid[rw][cl].node)
              node_closest.insert(n);
          }
        }


        // for each node find membership
        for (const auto &n : node_closest)
        {
          int wn;
          point_base pw;
          pw.ilat = n->ilat;
          pw.ilon = n->ilon;
          wn = pga.second.winding_number_algo(pw.ilat, pw.ilon);
          if (wn != 0)
            pga.second.node_in.push_back(n);
        }
      }

      string basename;
      if (jconf.has_member("cartout_basename"))
        basename = jconf["cartout_basename"].as<std::string>();
      else
        basename = "ace_score";

      ofstream out_score(basename + ".csv");
      out_score << "node_cid;node_lid;score;city" << std::endl;
      for (const auto &pg : polygons_ace) {
        for (const auto &n : pg.second.node_in)
          out_score << n->cid << ";" << n->lid << ";" << pg.second.score << ";" << pg.second.pro.at("COM_NAME") << std::endl;
      }
      std::cout << "Score ace file dumped in: " << basename + ".csv" << std::endl;
      return 0;
    }

    if (jconf.has_member("file_latlon_noturn")){
      c->dump_noturn_file(jconf["file_latlon_noturn"].as<std::string>());
    }
    
    c->dump_edited();
    c->dump_test_config();
  }
  catch (exception &e)
  {
    cerr << "EXC: " << e.what() << endl;
    exit(1);
  }

  return 0;
}
