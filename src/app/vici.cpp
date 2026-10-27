#include <iostream>
#include <carto.h>
#include <vici_gui.h>

using namespace std;
using namespace jsoncons;

constexpr int MAJOR = 4;
constexpr int MINOR = 0;

int FRAME_PER_DT;

void usage(const char* progname)
{
  string pn(progname);
  cerr << "Usage: " << pn.substr(pn.find_last_of("/\\") + 1) << " path/to/json/config" << endl;
  cerr << R"(JSON CONFIG SAMPLE
{
  "file_pro"     : "roads.pro",      // poly properties input file
  "file_pnt"     : "roads.pnt",      // poly geometry input file
  "enable_gui"   : true,             // fltk gui
  "pawns" :                          // pawns spec subjson
  {
    "type_name" : {
      "number" : 5,
      "start_poly_lid" : 0,
      "speed_mps" : 1.0
    }
  }
}
)";
}

int main(int argc, char** argv)
{
  cout << "ViCi (Virtual City Simulator) v" << MAJOR << "." << MINOR << endl;

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

  json jconf;
  try
  {
    jconf = json::parse_file(conf);
    // Init cart
    cart c(jconf);
    std::cout << c.info() << std::endl;
    // Init simulation
    if (jconf.has_member("frame_per_dt"))
      FRAME_PER_DT = jconf["frame_per_dt"].as<int>();
    else
      FRAME_PER_DT = 20;
    simulation s(jconf, &c);
    std::cout << s.info() << std::endl;

    // Init graphics and run
    if (jconf.has_member("enable_gui") && jconf["enable_gui"].as<bool>())
    {
      // Gui
      gui g(&c, &s);

      if (jconf.has_member("sampling_graphics"))
      {
        try
        {
          s.sampling_dt = jconf["sampling_graphics"].as<int>();
          cout << "[vici] Overriding parameters 'sampling_dt' to " << s.sampling_dt << endl;
        }
        catch(std::exception &e)
        {
          cerr << "[vici] Override graphics dt sampling EXC : " << e.what() << endl;
        }
      }

      // Display stuff
      g.run();
      cout << "[vici] simulation done, iter " << s.iter << endl;
    }
  }
  catch (exception &e)
  {
    cerr << "[vici] Generic EXC : " << e.what() << endl;
    exit(1);
  }
}
