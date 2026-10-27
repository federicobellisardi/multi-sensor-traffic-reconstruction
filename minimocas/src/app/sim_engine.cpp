#include <iostream>
#include <sstream>
#include <thread>
#include <vector>

#include <jsoncons/json.hpp>

#include <physycom/time.hpp>

#include <simulation.h>

using namespace std;
using namespace jsoncons;

constexpr int MAJOR = 2;
constexpr int MINOR = 0;

void usage(const char* progname)
{
  string pn(progname);
  cerr << "Usage: " << pn.substr(pn.find_last_of("/\\") + 1) << " path/to/json/config" << endl;
}

int main(int argc, char** argv)
{
  cout << "simulation engine v" << MAJOR << "." << MINOR << endl;

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
    json jconf;
    jconf = json::parse_file(conf);

    // Init cart
    cart c(jconf);
    std::cout << c.info() << std::endl;

    // init simulation
    simulation s(jconf, &c);
    std::cout << s.info() << std::endl;

    s.run([&s](){
      s.dump_net_state();
      s.dump_influxgrid();
      s.dump_polygons();
      s.dump_population();
      s.dump_pawn_state();
      s.dump_sources();
    }, [](){});
    s.dump_barriers();
    s.dump_geodata();
    s.dump_poly_uniq();
    c.dump_poly_geojson("er-carto");
    s.grid.dump_geojson("er-grid.geojson");
    cout << "[sim_engine] simulation done, iter " << s.iter << endl;
  }
  catch (exception &e)
  {
    cerr << "[sim_engine] EXC: " << e.what() << endl;
  }

  return 0;
}
