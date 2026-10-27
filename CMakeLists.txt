cmake_minimum_required (VERSION 3.11)
project(covid_hep)

if (EXISTS "$ENV{WORKSPACE}/sysconfig/cmake/physycom_config.cmake")
  message(STATUS "Enabling physycom settings")
  include("$ENV{WORKSPACE}/sysconfig/cmake/physycom_config.cmake")
else()
  message(STATUS "Unable to find physycom settings file")
endif()
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_INSTALL_RPATH ${CMAKE_CURRENT_LIST_DIR}/bin)

include(minimocas/CMakeLists.txt)
add_subdirectory($ENV{WORKSPACE}/pybind11 pybind11)

set(WORKSPACE $ENV{WORKSPACE})
string(REPLACE "\\" "/" WORKSPACE ${WORKSPACE})

add_executable(autodir
  ${CMAKE_CURRENT_LIST_DIR}/src/app/autodir.cpp
)
target_link_libraries(autodir
  carto
  simulation_deps
  Threads::Threads
  ${common_libs}
)

pybind11_add_module(pysim
  ${CMAKE_CURRENT_LIST_DIR}/src/python_interface.cpp
  # ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/lib/carto.cpp
  # ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/lib/carto_bestpath.cpp
  # ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/lib/carto_edit.cpp
  # ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/lib/simulation.cpp
  # ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/lib/simulation_io.cpp
  # ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/lib/pawn.cpp
)
target_link_libraries(pysim PRIVATE
  carto
  simulation_deps
  Boost::system
  Boost::filesystem
)
install(TARGETS pysim DESTINATION ${CMAKE_CURRENT_LIST_DIR}/bin)
install(TARGETS simulation_deps DESTINATION ${CMAKE_CURRENT_LIST_DIR}/bin)
install(TARGETS carto DESTINATION ${CMAKE_CURRENT_LIST_DIR}/bin)

# MINIMOCAS-TOOLS

include_directories(
  ${CMAKE_CURRENT_LIST_DIR}/src/
  ${CMAKE_CURRENT_LIST_DIR}/src/app
)

find_package(FLTK 1.3.3 REQUIRED)
find_package(OpenGL REQUIRED)

include_directories(
  ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/lib
  ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/jsoncons/include
  ${CMAKE_CURRENT_LIST_DIR}/minimocas/src/utils
  ${FLTK_INCLUDE_DIR}
)

add_library(minitest_deps
  ${CMAKE_CURRENT_LIST_DIR}/src/app/minitest_layout.cpp
  ${CMAKE_CURRENT_LIST_DIR}/src/app/minitest_scene.cpp
)
add_executable(minitest
  ${CMAKE_CURRENT_LIST_DIR}/src/app/minitest.cpp
)
target_link_libraries(minitest
  minitest_deps
  carto
  ${FLTK_LIBRARIES}
  ${OPENGL_LIBRARIES}
  Threads::Threads
  ${common_libs}
)

add_executable(miniedit
  ${CMAKE_CURRENT_LIST_DIR}/src/app/miniedit.cpp
)
target_link_libraries(miniedit
  carto
  Threads::Threads
  ${common_libs}
)

add_executable(vici
  ${CMAKE_CURRENT_LIST_DIR}/src/app/vici.cpp
  ${CMAKE_CURRENT_LIST_DIR}/src/app/vici_layout.cpp
  ${CMAKE_CURRENT_LIST_DIR}/src/app/vici_scene.cpp
)
target_link_libraries(vici
  carto
  simulation_deps
  ${FLTK_LIBRARIES}
  ${OPENGL_LIBRARIES}
  Threads::Threads
  ${common_libs}
)


# CONFIG
configure_file(
  ${CMAKE_CURRENT_LIST_DIR}/vars/templates/sim_template.json.in
  ${CMAKE_CURRENT_LIST_DIR}/vars/templates/sim_template.json
)
configure_file(
  ${CMAKE_CURRENT_LIST_DIR}/vars/templates/check_template.json.in
  ${CMAKE_CURRENT_LIST_DIR}/vars/templates/check_template.json
)
# replace \ with / in windows path
if (MSVC)
  file(READ ${CMAKE_CURRENT_LIST_DIR}/vars/templates/sim_template.json TEMPLATE_SIM)
  string(REPLACE "\\" "/" TEMPLATE_SIM_ESC ${TEMPLATE_SIM} )
  file(WRITE ${CMAKE_CURRENT_LIST_DIR}/vars/templates/sim_template.json ${TEMPLATE_SIM_ESC})
endif()
