#include <iostream>
#include <sstream>
#include <thread>
#include <vector>

#include <jsoncons/json.hpp>

#include <physycom/time.hpp>

#include <simulation.h>

using namespace std;
using namespace jsoncons;

constexpr int MAJOR = 1;
constexpr int MINOR = 0;

void usage(const char* progname)
{
  string pn(progname);
  cerr << "Usage: " << pn.substr(pn.find_last_of("/\\") + 1) << " path/to/json/config" << endl;
}

int main(int argc, char** argv)
{
  cout << "auto direction detector v" << MAJOR << "." << MINOR << endl;

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

    // init cart
    cart c(jconf);
    std::cout << c.info() << std::endl;

    // init simulation
    simulation s(jconf, &c);
    std::cout << s.info() << std::endl;



  }
  catch (exception &e)
  {
    cerr << "[sim_engine] EXC: " << e.what() << endl;
  }
}
