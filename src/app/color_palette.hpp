/*!
 *  \file   color_palette.hpp
 *  \author A. Fabbri (alessandro.fabbri27@unibo.it), C. Mizzi (chiara.mizzi2@unibo.it), S. Sinigardi (stefano.sinigardi@unibo.it)
 *  \brief  Some OpenGL based palette.
 *  \details This file contains the implementation of a number of palette of colors, based on OpenGL.
 *
 */

#ifndef _MINIMOCAS_COLOR_PALETTE_HPP_
#define _MINIMOCAS_COLOR_PALETTE_HPP_

static void __color_palette(const int &i)
{
  switch (i % 3)
  {
    case 0:  glColor3d(198.f / 255.f,  44.f / 255.f,   1.f / 255.f); break;   // red
    case 1:  glColor3d(198.f / 255.f, 194.f / 255.f,   1.f / 255.f); break;   // lime
    case 2:  glColor3d(172.f / 255.f,  44.f / 255.f, 247.f / 255.f); break;   // purple
    default: glColor3d(  0.f / 255.f,   0.f / 255.f,   0.f / 255.f); break;   // black
  }
}

enum
{
  WHITE = 255,
  BLACK = 0,
  RED = 9,
  BLUE = 21,
  GREY = 236,
  LIGHTBLUE = 146,
  DARKGREEN = 22,
  MAGENTA = 201,
  ORANGE = 166,
  TURQUOISE = 30
};

static void color_palette(const int &i)
{
  switch( i % 256 )
  {
    case    0:  glColor3d(   0.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // Black
    case    1:  glColor3d( 128.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // Maroon
    case    2:  glColor3d(   0.f / 255.f,  128.f / 255.f,    0.f / 255.f); break;   // Green
    case    3:  glColor3d( 128.f / 255.f,  128.f / 255.f,    0.f / 255.f); break;   // Olive
    case    4:  glColor3d(   0.f / 255.f,    0.f / 255.f,  128.f / 255.f); break;   // Navy
    case    5:  glColor3d( 128.f / 255.f,    0.f / 255.f,  128.f / 255.f); break;   // Purple
    case    6:  glColor3d(   0.f / 255.f,  128.f / 255.f,  128.f / 255.f); break;   // Teal
    case    7:  glColor3d( 192.f / 255.f,  192.f / 255.f,  192.f / 255.f); break;   // Silver
    case    8:  glColor3d( 128.f / 255.f,  128.f / 255.f,  128.f / 255.f); break;   // Grey
    case    9:  glColor3d( 255.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // Red
    case   10:  glColor3d(   0.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // Lime
    case   11:  glColor3d( 255.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // Yellow
    case   12:  glColor3d(   0.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // Blue
    case   13:  glColor3d( 255.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // Fuchsia
    case   14:  glColor3d(   0.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // Aqua
    case   15:  glColor3d( 255.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // White
    case   16:  glColor3d(   0.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // Grey0
    case   17:  glColor3d(   0.f / 255.f,    0.f / 255.f,   95.f / 255.f); break;   // NavyBlue
    case   18:  glColor3d(   0.f / 255.f,    0.f / 255.f,  135.f / 255.f); break;   // DarkBlue
    case   19:  glColor3d(   0.f / 255.f,    0.f / 255.f,  175.f / 255.f); break;   // Blue3
    case   20:  glColor3d(   0.f / 255.f,    0.f / 255.f,  215.f / 255.f); break;   // Blue3
    case   21:  glColor3d(   0.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // Blue1
    case   22:  glColor3d(   0.f / 255.f,   95.f / 255.f,    0.f / 255.f); break;   // DarkGreen
    case   23:  glColor3d(   0.f / 255.f,   95.f / 255.f,   95.f / 255.f); break;   // DeepSkyBlue4
    case   24:  glColor3d(   0.f / 255.f,   95.f / 255.f,  135.f / 255.f); break;   // DeepSkyBlue4
    case   25:  glColor3d(   0.f / 255.f,   95.f / 255.f,  175.f / 255.f); break;   // DeepSkyBlue4
    case   26:  glColor3d(   0.f / 255.f,   95.f / 255.f,  215.f / 255.f); break;   // DodgerBlue3
    case   27:  glColor3d(   0.f / 255.f,   95.f / 255.f,  255.f / 255.f); break;   // DodgerBlue2
    case   28:  glColor3d(   0.f / 255.f,  135.f / 255.f,    0.f / 255.f); break;   // Green4
    case   29:  glColor3d(   0.f / 255.f,  135.f / 255.f,   95.f / 255.f); break;   // SpringGreen4
    case   30:  glColor3d(   0.f / 255.f,  135.f / 255.f,  135.f / 255.f); break;   // Turquoise4
    case   31:  glColor3d(   0.f / 255.f,  135.f / 255.f,  175.f / 255.f); break;   // DeepSkyBlue3
    case   32:  glColor3d(   0.f / 255.f,  135.f / 255.f,  215.f / 255.f); break;   // DeepSkyBlue3
    case   33:  glColor3d(   0.f / 255.f,  135.f / 255.f,  255.f / 255.f); break;   // DodgerBlue1
    case   34:  glColor3d(   0.f / 255.f,  175.f / 255.f,    0.f / 255.f); break;   // Green3
    case   35:  glColor3d(   0.f / 255.f,  175.f / 255.f,   95.f / 255.f); break;   // SpringGreen3
    case   36:  glColor3d(   0.f / 255.f,  175.f / 255.f,  135.f / 255.f); break;   // DarkCyan
    case   37:  glColor3d(   0.f / 255.f,  175.f / 255.f,  175.f / 255.f); break;   // LightSeaGreen
    case   38:  glColor3d(   0.f / 255.f,  175.f / 255.f,  215.f / 255.f); break;   // DeepSkyBlue2
    case   39:  glColor3d(   0.f / 255.f,  175.f / 255.f,  255.f / 255.f); break;   // DeepSkyBlue1
    case   40:  glColor3d(   0.f / 255.f,  215.f / 255.f,    0.f / 255.f); break;   // Green3
    case   41:  glColor3d(   0.f / 255.f,  215.f / 255.f,   95.f / 255.f); break;   // SpringGreen3
    case   42:  glColor3d(   0.f / 255.f,  215.f / 255.f,  135.f / 255.f); break;   // SpringGreen2
    case   43:  glColor3d(   0.f / 255.f,  215.f / 255.f,  175.f / 255.f); break;   // Cyan3
    case   44:  glColor3d(   0.f / 255.f,  215.f / 255.f,  215.f / 255.f); break;   // DarkTurquoise
    case   45:  glColor3d(   0.f / 255.f,  215.f / 255.f,  255.f / 255.f); break;   // Turquoise2
    case   46:  glColor3d(   0.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // Green1
    case   47:  glColor3d(   0.f / 255.f,  255.f / 255.f,   95.f / 255.f); break;   // SpringGreen2
    case   48:  glColor3d(   0.f / 255.f,  255.f / 255.f,  135.f / 255.f); break;   // SpringGreen1
    case   49:  glColor3d(   0.f / 255.f,  255.f / 255.f,  175.f / 255.f); break;   // MediumSpringGreen
    case   50:  glColor3d(   0.f / 255.f,  255.f / 255.f,  215.f / 255.f); break;   // Cyan2
    case   51:  glColor3d(   0.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // Cyan1
    case   52:  glColor3d(  95.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // DarkRed
    case   53:  glColor3d(  95.f / 255.f,    0.f / 255.f,   95.f / 255.f); break;   // DeepPink4
    case   54:  glColor3d(  95.f / 255.f,    0.f / 255.f,  135.f / 255.f); break;   // Purple4
    case   55:  glColor3d(  95.f / 255.f,    0.f / 255.f,  175.f / 255.f); break;   // Purple4
    case   56:  glColor3d(  95.f / 255.f,    0.f / 255.f,  215.f / 255.f); break;   // Purple3
    case   57:  glColor3d(  95.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // BlueViolet
    case   58:  glColor3d(  95.f / 255.f,   95.f / 255.f,    0.f / 255.f); break;   // Orange4
    case   59:  glColor3d(  95.f / 255.f,   95.f / 255.f,   95.f / 255.f); break;   // Grey37
    case   60:  glColor3d(  95.f / 255.f,   95.f / 255.f,  135.f / 255.f); break;   // MediumPurple4
    case   61:  glColor3d(  95.f / 255.f,   95.f / 255.f,  175.f / 255.f); break;   // SlateBlue3
    case   62:  glColor3d(  95.f / 255.f,   95.f / 255.f,  215.f / 255.f); break;   // SlateBlue3
    case   63:  glColor3d(  95.f / 255.f,   95.f / 255.f,  255.f / 255.f); break;   // RoyalBlue1
    case   64:  glColor3d(  95.f / 255.f,  135.f / 255.f,    0.f / 255.f); break;   // Chartreuse4
    case   65:  glColor3d(  95.f / 255.f,  135.f / 255.f,   95.f / 255.f); break;   // DarkSeaGreen4
    case   66:  glColor3d(  95.f / 255.f,  135.f / 255.f,  135.f / 255.f); break;   // PaleTurquoise4
    case   67:  glColor3d(  95.f / 255.f,  135.f / 255.f,  175.f / 255.f); break;   // SteelBlue
    case   68:  glColor3d(  95.f / 255.f,  135.f / 255.f,  215.f / 255.f); break;   // SteelBlue3
    case   69:  glColor3d(  95.f / 255.f,  135.f / 255.f,  255.f / 255.f); break;   // CornflowerBlue
    case   70:  glColor3d(  95.f / 255.f,  175.f / 255.f,    0.f / 255.f); break;   // Chartreuse3
    case   71:  glColor3d(  95.f / 255.f,  175.f / 255.f,   95.f / 255.f); break;   // DarkSeaGreen4
    case   72:  glColor3d(  95.f / 255.f,  175.f / 255.f,  135.f / 255.f); break;   // CadetBlue
    case   73:  glColor3d(  95.f / 255.f,  175.f / 255.f,  175.f / 255.f); break;   // CadetBlue
    case   74:  glColor3d(  95.f / 255.f,  175.f / 255.f,  215.f / 255.f); break;   // SkyBlue3
    case   75:  glColor3d(  95.f / 255.f,  175.f / 255.f,  255.f / 255.f); break;   // SteelBlue1
    case   76:  glColor3d(  95.f / 255.f,  215.f / 255.f,    0.f / 255.f); break;   // Chartreuse3
    case   77:  glColor3d(  95.f / 255.f,  215.f / 255.f,   95.f / 255.f); break;   // PaleGreen3
    case   78:  glColor3d(  95.f / 255.f,  215.f / 255.f,  135.f / 255.f); break;   // SeaGreen3
    case   79:  glColor3d(  95.f / 255.f,  215.f / 255.f,  175.f / 255.f); break;   // Aquamarine3
    case   80:  glColor3d(  95.f / 255.f,  215.f / 255.f,  215.f / 255.f); break;   // MediumTurquoise
    case   81:  glColor3d(  95.f / 255.f,  215.f / 255.f,  255.f / 255.f); break;   // SteelBlue1
    case   82:  glColor3d(  95.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // Chartreuse2
    case   83:  glColor3d(  95.f / 255.f,  255.f / 255.f,   95.f / 255.f); break;   // SeaGreen2
    case   84:  glColor3d(  95.f / 255.f,  255.f / 255.f,  135.f / 255.f); break;   // SeaGreen1
    case   85:  glColor3d(  95.f / 255.f,  255.f / 255.f,  175.f / 255.f); break;   // SeaGreen1
    case   86:  glColor3d(  95.f / 255.f,  255.f / 255.f,  215.f / 255.f); break;   // Aquamarine1
    case   87:  glColor3d(  95.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // DarkSlateGray2
    case   88:  glColor3d( 135.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // DarkRed
    case   89:  glColor3d( 135.f / 255.f,    0.f / 255.f,   95.f / 255.f); break;   // DeepPink4
    case   90:  glColor3d( 135.f / 255.f,    0.f / 255.f,  135.f / 255.f); break;   // DarkMagenta
    case   91:  glColor3d( 135.f / 255.f,    0.f / 255.f,  175.f / 255.f); break;   // DarkMagenta
    case   92:  glColor3d( 135.f / 255.f,    0.f / 255.f,  215.f / 255.f); break;   // DarkViolet
    case   93:  glColor3d( 135.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // Purple
    case   94:  glColor3d( 135.f / 255.f,   95.f / 255.f,    0.f / 255.f); break;   // Orange4
    case   95:  glColor3d( 135.f / 255.f,   95.f / 255.f,   95.f / 255.f); break;   // LightPink4
    case   96:  glColor3d( 135.f / 255.f,   95.f / 255.f,  135.f / 255.f); break;   // Plum4
    case   97:  glColor3d( 135.f / 255.f,   95.f / 255.f,  175.f / 255.f); break;   // MediumPurple3
    case   98:  glColor3d( 135.f / 255.f,   95.f / 255.f,  215.f / 255.f); break;   // MediumPurple3
    case   99:  glColor3d( 135.f / 255.f,   95.f / 255.f,  255.f / 255.f); break;   // SlateBlue1
    case  100:  glColor3d( 135.f / 255.f,  135.f / 255.f,    0.f / 255.f); break;   // Yellow4
    case  101:  glColor3d( 135.f / 255.f,  135.f / 255.f,   95.f / 255.f); break;   // Wheat4
    case  102:  glColor3d( 135.f / 255.f,  135.f / 255.f,  135.f / 255.f); break;   // Grey53
    case  103:  glColor3d( 135.f / 255.f,  135.f / 255.f,  175.f / 255.f); break;   // LightSlateGrey
    case  104:  glColor3d( 135.f / 255.f,  135.f / 255.f,  215.f / 255.f); break;   // MediumPurple
    case  105:  glColor3d( 135.f / 255.f,  135.f / 255.f,  255.f / 255.f); break;   // LightSlateBlue
    case  106:  glColor3d( 135.f / 255.f,  175.f / 255.f,    0.f / 255.f); break;   // Yellow4
    case  107:  glColor3d( 135.f / 255.f,  175.f / 255.f,   95.f / 255.f); break;   // DarkOliveGreen3
    case  108:  glColor3d( 135.f / 255.f,  175.f / 255.f,  135.f / 255.f); break;   // DarkSeaGreen
    case  109:  glColor3d( 135.f / 255.f,  175.f / 255.f,  175.f / 255.f); break;   // LightSkyBlue3
    case  110:  glColor3d( 135.f / 255.f,  175.f / 255.f,  215.f / 255.f); break;   // LightSkyBlue3
    case  111:  glColor3d( 135.f / 255.f,  175.f / 255.f,  255.f / 255.f); break;   // SkyBlue2
    case  112:  glColor3d( 135.f / 255.f,  215.f / 255.f,    0.f / 255.f); break;   // Chartreuse2
    case  113:  glColor3d( 135.f / 255.f,  215.f / 255.f,   95.f / 255.f); break;   // DarkOliveGreen3
    case  114:  glColor3d( 135.f / 255.f,  215.f / 255.f,  135.f / 255.f); break;   // PaleGreen3
    case  115:  glColor3d( 135.f / 255.f,  215.f / 255.f,  175.f / 255.f); break;   // DarkSeaGreen3
    case  116:  glColor3d( 135.f / 255.f,  215.f / 255.f,  215.f / 255.f); break;   // DarkSlateGray3
    case  117:  glColor3d( 135.f / 255.f,  215.f / 255.f,  255.f / 255.f); break;   // SkyBlue1
    case  118:  glColor3d( 135.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // Chartreuse1
    case  119:  glColor3d( 135.f / 255.f,  255.f / 255.f,   95.f / 255.f); break;   // LightGreen
    case  120:  glColor3d( 135.f / 255.f,  255.f / 255.f,  135.f / 255.f); break;   // LightGreen
    case  121:  glColor3d( 135.f / 255.f,  255.f / 255.f,  175.f / 255.f); break;   // PaleGreen1
    case  122:  glColor3d( 135.f / 255.f,  255.f / 255.f,  215.f / 255.f); break;   // Aquamarine1
    case  123:  glColor3d( 135.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // DarkSlateGray1
    case  124:  glColor3d( 175.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // Red3
    case  125:  glColor3d( 175.f / 255.f,    0.f / 255.f,   95.f / 255.f); break;   // DeepPink4
    case  126:  glColor3d( 175.f / 255.f,    0.f / 255.f,  135.f / 255.f); break;   // MediumVioletRed
    case  127:  glColor3d( 175.f / 255.f,    0.f / 255.f,  175.f / 255.f); break;   // Magenta3
    case  128:  glColor3d( 175.f / 255.f,    0.f / 255.f,  215.f / 255.f); break;   // DarkViolet
    case  129:  glColor3d( 175.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // Purple
    case  130:  glColor3d( 175.f / 255.f,   95.f / 255.f,    0.f / 255.f); break;   // DarkOrange3
    case  131:  glColor3d( 175.f / 255.f,   95.f / 255.f,   95.f / 255.f); break;   // IndianRed
    case  132:  glColor3d( 175.f / 255.f,   95.f / 255.f,  135.f / 255.f); break;   // HotPink3
    case  133:  glColor3d( 175.f / 255.f,   95.f / 255.f,  175.f / 255.f); break;   // MediumOrchid3
    case  134:  glColor3d( 175.f / 255.f,   95.f / 255.f,  215.f / 255.f); break;   // MediumOrchid
    case  135:  glColor3d( 175.f / 255.f,   95.f / 255.f,  255.f / 255.f); break;   // MediumPurple2
    case  136:  glColor3d( 175.f / 255.f,  135.f / 255.f,    0.f / 255.f); break;   // DarkGoldenrod
    case  137:  glColor3d( 175.f / 255.f,  135.f / 255.f,   95.f / 255.f); break;   // LightSalmon3
    case  138:  glColor3d( 175.f / 255.f,  135.f / 255.f,  135.f / 255.f); break;   // RosyBrown
    case  139:  glColor3d( 175.f / 255.f,  135.f / 255.f,  175.f / 255.f); break;   // Grey63
    case  140:  glColor3d( 175.f / 255.f,  135.f / 255.f,  215.f / 255.f); break;   // MediumPurple2
    case  141:  glColor3d( 175.f / 255.f,  135.f / 255.f,  255.f / 255.f); break;   // MediumPurple1
    case  142:  glColor3d( 175.f / 255.f,  175.f / 255.f,    0.f / 255.f); break;   // Gold3
    case  143:  glColor3d( 175.f / 255.f,  175.f / 255.f,   95.f / 255.f); break;   // DarkKhaki
    case  144:  glColor3d( 175.f / 255.f,  175.f / 255.f,  135.f / 255.f); break;   // NavajoWhite3
    case  145:  glColor3d( 175.f / 255.f,  175.f / 255.f,  175.f / 255.f); break;   // Grey69
    case  146:  glColor3d( 175.f / 255.f,  175.f / 255.f,  215.f / 255.f); break;   // LightSteelBlue3
    case  147:  glColor3d( 175.f / 255.f,  175.f / 255.f,  255.f / 255.f); break;   // LightSteelBlue
    case  148:  glColor3d( 175.f / 255.f,  215.f / 255.f,    0.f / 255.f); break;   // Yellow3
    case  149:  glColor3d( 175.f / 255.f,  215.f / 255.f,   95.f / 255.f); break;   // DarkOliveGreen3
    case  150:  glColor3d( 175.f / 255.f,  215.f / 255.f,  135.f / 255.f); break;   // DarkSeaGreen3
    case  151:  glColor3d( 175.f / 255.f,  215.f / 255.f,  175.f / 255.f); break;   // DarkSeaGreen2
    case  152:  glColor3d( 175.f / 255.f,  215.f / 255.f,  215.f / 255.f); break;   // LightCyan3
    case  153:  glColor3d( 175.f / 255.f,  215.f / 255.f,  255.f / 255.f); break;   // LightSkyBlue1
    case  154:  glColor3d( 175.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // GreenYellow
    case  155:  glColor3d( 175.f / 255.f,  255.f / 255.f,   95.f / 255.f); break;   // DarkOliveGreen2
    case  156:  glColor3d( 175.f / 255.f,  255.f / 255.f,  135.f / 255.f); break;   // PaleGreen1
    case  157:  glColor3d( 175.f / 255.f,  255.f / 255.f,  175.f / 255.f); break;   // DarkSeaGreen2
    case  158:  glColor3d( 175.f / 255.f,  255.f / 255.f,  215.f / 255.f); break;   // DarkSeaGreen1
    case  159:  glColor3d( 175.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // PaleTurquoise1
    case  160:  glColor3d( 215.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // Red3
    case  161:  glColor3d( 215.f / 255.f,    0.f / 255.f,   95.f / 255.f); break;   // DeepPink3
    case  162:  glColor3d( 215.f / 255.f,    0.f / 255.f,  135.f / 255.f); break;   // DeepPink3
    case  163:  glColor3d( 215.f / 255.f,    0.f / 255.f,  175.f / 255.f); break;   // Magenta3
    case  164:  glColor3d( 215.f / 255.f,    0.f / 255.f,  215.f / 255.f); break;   // Magenta3
    case  165:  glColor3d( 215.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // Magenta2
    case  166:  glColor3d( 215.f / 255.f,   95.f / 255.f,    0.f / 255.f); break;   // DarkOrange3
    case  167:  glColor3d( 215.f / 255.f,   95.f / 255.f,   95.f / 255.f); break;   // IndianRed
    case  168:  glColor3d( 215.f / 255.f,   95.f / 255.f,  135.f / 255.f); break;   // HotPink3
    case  169:  glColor3d( 215.f / 255.f,   95.f / 255.f,  175.f / 255.f); break;   // HotPink2
    case  170:  glColor3d( 215.f / 255.f,   95.f / 255.f,  215.f / 255.f); break;   // Orchid
    case  171:  glColor3d( 215.f / 255.f,   95.f / 255.f,  255.f / 255.f); break;   // MediumOrchid1
    case  172:  glColor3d( 215.f / 255.f,  135.f / 255.f,    0.f / 255.f); break;   // Orange3
    case  173:  glColor3d( 215.f / 255.f,  135.f / 255.f,   95.f / 255.f); break;   // LightSalmon3
    case  174:  glColor3d( 215.f / 255.f,  135.f / 255.f,  135.f / 255.f); break;   // LightPink3
    case  175:  glColor3d( 215.f / 255.f,  135.f / 255.f,  175.f / 255.f); break;   // Pink3
    case  176:  glColor3d( 215.f / 255.f,  135.f / 255.f,  215.f / 255.f); break;   // Plum3
    case  177:  glColor3d( 215.f / 255.f,  135.f / 255.f,  255.f / 255.f); break;   // Violet
    case  178:  glColor3d( 215.f / 255.f,  175.f / 255.f,    0.f / 255.f); break;   // Gold3
    case  179:  glColor3d( 215.f / 255.f,  175.f / 255.f,   95.f / 255.f); break;   // LightGoldenrod3
    case  180:  glColor3d( 215.f / 255.f,  175.f / 255.f,  135.f / 255.f); break;   // Tan
    case  181:  glColor3d( 215.f / 255.f,  175.f / 255.f,  175.f / 255.f); break;   // MistyRose3
    case  182:  glColor3d( 215.f / 255.f,  175.f / 255.f,  215.f / 255.f); break;   // Thistle3
    case  183:  glColor3d( 215.f / 255.f,  175.f / 255.f,  255.f / 255.f); break;   // Plum2
    case  184:  glColor3d( 215.f / 255.f,  215.f / 255.f,    0.f / 255.f); break;   // Yellow3
    case  185:  glColor3d( 215.f / 255.f,  215.f / 255.f,   95.f / 255.f); break;   // Khaki3
    case  186:  glColor3d( 215.f / 255.f,  215.f / 255.f,  135.f / 255.f); break;   // LightGoldenrod2
    case  187:  glColor3d( 215.f / 255.f,  215.f / 255.f,  175.f / 255.f); break;   // LightYellow3
    case  188:  glColor3d( 215.f / 255.f,  215.f / 255.f,  215.f / 255.f); break;   // Grey84
    case  189:  glColor3d( 215.f / 255.f,  215.f / 255.f,  255.f / 255.f); break;   // LightSteelBlue1
    case  190:  glColor3d( 215.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // Yellow2
    case  191:  glColor3d( 215.f / 255.f,  255.f / 255.f,   95.f / 255.f); break;   // DarkOliveGreen1
    case  192:  glColor3d( 215.f / 255.f,  255.f / 255.f,  135.f / 255.f); break;   // DarkOliveGreen1
    case  193:  glColor3d( 215.f / 255.f,  255.f / 255.f,  175.f / 255.f); break;   // DarkSeaGreen1
    case  194:  glColor3d( 215.f / 255.f,  255.f / 255.f,  215.f / 255.f); break;   // Honeydew2
    case  195:  glColor3d( 215.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // LightCyan1
    case  196:  glColor3d( 255.f / 255.f,    0.f / 255.f,    0.f / 255.f); break;   // Red1
    case  197:  glColor3d( 255.f / 255.f,    0.f / 255.f,   95.f / 255.f); break;   // DeepPink2
    case  198:  glColor3d( 255.f / 255.f,    0.f / 255.f,  135.f / 255.f); break;   // DeepPink1
    case  199:  glColor3d( 255.f / 255.f,    0.f / 255.f,  175.f / 255.f); break;   // DeepPink1
    case  200:  glColor3d( 255.f / 255.f,    0.f / 255.f,  215.f / 255.f); break;   // Magenta2
    case  201:  glColor3d( 255.f / 255.f,    0.f / 255.f,  255.f / 255.f); break;   // Magenta1
    case  202:  glColor3d( 255.f / 255.f,   95.f / 255.f,    0.f / 255.f); break;   // OrangeRed1
    case  203:  glColor3d( 255.f / 255.f,   95.f / 255.f,   95.f / 255.f); break;   // IndianRed1
    case  204:  glColor3d( 255.f / 255.f,   95.f / 255.f,  135.f / 255.f); break;   // IndianRed1
    case  205:  glColor3d( 255.f / 255.f,   95.f / 255.f,  175.f / 255.f); break;   // HotPink
    case  206:  glColor3d( 255.f / 255.f,   95.f / 255.f,  215.f / 255.f); break;   // HotPink
    case  207:  glColor3d( 255.f / 255.f,   95.f / 255.f,  255.f / 255.f); break;   // MediumOrchid1
    case  208:  glColor3d( 255.f / 255.f,  135.f / 255.f,    0.f / 255.f); break;   // DarkOrange
    case  209:  glColor3d( 255.f / 255.f,  135.f / 255.f,   95.f / 255.f); break;   // Salmon1
    case  210:  glColor3d( 255.f / 255.f,  135.f / 255.f,  135.f / 255.f); break;   // LightCoral
    case  211:  glColor3d( 255.f / 255.f,  135.f / 255.f,  175.f / 255.f); break;   // PaleVioletRed1
    case  212:  glColor3d( 255.f / 255.f,  135.f / 255.f,  215.f / 255.f); break;   // Orchid2
    case  213:  glColor3d( 255.f / 255.f,  135.f / 255.f,  255.f / 255.f); break;   // Orchid1
    case  214:  glColor3d( 255.f / 255.f,  175.f / 255.f,    0.f / 255.f); break;   // Orange1
    case  215:  glColor3d( 255.f / 255.f,  175.f / 255.f,   95.f / 255.f); break;   // SandyBrown
    case  216:  glColor3d( 255.f / 255.f,  175.f / 255.f,  135.f / 255.f); break;   // LightSalmon1
    case  217:  glColor3d( 255.f / 255.f,  175.f / 255.f,  175.f / 255.f); break;   // LightPink1
    case  218:  glColor3d( 255.f / 255.f,  175.f / 255.f,  215.f / 255.f); break;   // Pink1
    case  219:  glColor3d( 255.f / 255.f,  175.f / 255.f,  255.f / 255.f); break;   // Plum1
    case  220:  glColor3d( 255.f / 255.f,  215.f / 255.f,    0.f / 255.f); break;   // Gold1
    case  221:  glColor3d( 255.f / 255.f,  215.f / 255.f,   95.f / 255.f); break;   // LightGoldenrod2
    case  222:  glColor3d( 255.f / 255.f,  215.f / 255.f,  135.f / 255.f); break;   // LightGoldenrod2
    case  223:  glColor3d( 255.f / 255.f,  215.f / 255.f,  175.f / 255.f); break;   // NavajoWhite1
    case  224:  glColor3d( 255.f / 255.f,  215.f / 255.f,  215.f / 255.f); break;   // MistyRose1
    case  225:  glColor3d( 255.f / 255.f,  215.f / 255.f,  255.f / 255.f); break;   // Thistle1
    case  226:  glColor3d( 255.f / 255.f,  255.f / 255.f,    0.f / 255.f); break;   // Yellow1
    case  227:  glColor3d( 255.f / 255.f,  255.f / 255.f,   95.f / 255.f); break;   // LightGoldenrod1
    case  228:  glColor3d( 255.f / 255.f,  255.f / 255.f,  135.f / 255.f); break;   // Khaki1
    case  229:  glColor3d( 255.f / 255.f,  255.f / 255.f,  175.f / 255.f); break;   // Wheat1
    case  230:  glColor3d( 255.f / 255.f,  255.f / 255.f,  215.f / 255.f); break;   // Cornsilk1
    case  231:  glColor3d( 255.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // Grey100
    case  232:  glColor3d(   8.f / 255.f,    8.f / 255.f,    8.f / 255.f); break;   // Grey3
    case  233:  glColor3d(  18.f / 255.f,   18.f / 255.f,   18.f / 255.f); break;   // Grey7
    case  234:  glColor3d(  28.f / 255.f,   28.f / 255.f,   28.f / 255.f); break;   // Grey11
    case  235:  glColor3d(  38.f / 255.f,   38.f / 255.f,   38.f / 255.f); break;   // Grey15
    case  236:  glColor3d(  48.f / 255.f,   48.f / 255.f,   48.f / 255.f); break;   // Grey19
    case  237:  glColor3d(  58.f / 255.f,   58.f / 255.f,   58.f / 255.f); break;   // Grey23
    case  238:  glColor3d(  68.f / 255.f,   68.f / 255.f,   68.f / 255.f); break;   // Grey27
    case  239:  glColor3d(  78.f / 255.f,   78.f / 255.f,   78.f / 255.f); break;   // Grey30
    case  240:  glColor3d(  88.f / 255.f,   88.f / 255.f,   88.f / 255.f); break;   // Grey35
    case  241:  glColor3d(  98.f / 255.f,   98.f / 255.f,   98.f / 255.f); break;   // Grey39
    case  242:  glColor3d( 108.f / 255.f,  108.f / 255.f,  108.f / 255.f); break;   // Grey42
    case  243:  glColor3d( 118.f / 255.f,  118.f / 255.f,  118.f / 255.f); break;   // Grey46
    case  244:  glColor3d( 128.f / 255.f,  128.f / 255.f,  128.f / 255.f); break;   // Grey50
    case  245:  glColor3d( 138.f / 255.f,  138.f / 255.f,  138.f / 255.f); break;   // Grey54
    case  246:  glColor3d( 148.f / 255.f,  148.f / 255.f,  148.f / 255.f); break;   // Grey58
    case  247:  glColor3d( 158.f / 255.f,  158.f / 255.f,  158.f / 255.f); break;   // Grey62
    case  248:  glColor3d( 168.f / 255.f,  168.f / 255.f,  168.f / 255.f); break;   // Grey66
    case  249:  glColor3d( 178.f / 255.f,  178.f / 255.f,  178.f / 255.f); break;   // Grey70
    case  250:  glColor3d( 188.f / 255.f,  188.f / 255.f,  188.f / 255.f); break;   // Grey74
    case  251:  glColor3d( 198.f / 255.f,  198.f / 255.f,  198.f / 255.f); break;   // Grey78
    case  252:  glColor3d( 208.f / 255.f,  208.f / 255.f,  208.f / 255.f); break;   // Grey82
    case  253:  glColor3d( 218.f / 255.f,  218.f / 255.f,  218.f / 255.f); break;   // Grey85
    case  254:  glColor3d( 228.f / 255.f,  228.f / 255.f,  228.f / 255.f); break;   // Grey89
    case  255:  glColor3d( 255.f / 255.f,  255.f / 255.f,  255.f / 255.f); break;   // white
  }
}

static constexpr int CMAP_LEN = 19;
static std::array<float, CMAP_LEN * 3> rgb_cmap{
  0.078431f, 0.078431f, 0.078431f, // 0
  0.266667f, 0.133333f, 0.600000f, // 1
  0.231373f, 0.047059f, 0.741176f, // 2
  0.200000f, 0.066667f, 0.733333f, // 3
  0.266667f, 0.266667f, 0.866667f, // 4
  0.066667f, 0.666667f, 0.733333f, // 5
  0.070588f, 0.741176f, 0.725490f, // 6
  0.133333f, 0.800000f, 0.666667f, // 7
  0.411765f, 0.815686f, 0.145098f, // 8
  0.666667f, 0.800000f, 0.133333f, // 9
  0.815686f, 0.764706f, 0.062745f, // 10
  0.800000f, 0.733333f, 0.200000f, // 11
  0.996078f, 0.682353f, 0.176471f, // 12
  1.000000f, 0.600000f, 0.200000f, // 13
  1.000000f, 0.400000f, 0.266667f, // 14
  1.000000f, 0.266667f, 0.133333f, // 15
  1.000000f, 0.200000f, 0.066667f, // 16
  0.933333f, 0.066667f, 0.000000f, // 17
  0.972549f, 0.047059f, 0.070588f  // 18
};

static void colormap(const double &x, const double &xmin, const double &xmax)
{
  int xn = int( (x - xmin)/(xmax - xmin) * CMAP_LEN );
  xn = xn < 0 ? 0 : xn;
  xn = xn > CMAP_LEN - 1 ? CMAP_LEN - 1 : xn;
  glColor3f( GLfloat(rgb_cmap[xn*3 + 0]), GLfloat(rgb_cmap[xn*3 + 1]), GLfloat(rgb_cmap[xn*3 + 2]) );
}

static void colormap(int i)
{
  i = i < 0 ? 0 : i;
  i = i > CMAP_LEN - 1 ? CMAP_LEN - 1 : i;
  glColor3f(GLfloat(rgb_cmap[i * 3 + 0]), GLfloat(rgb_cmap[i * 3 + 1]), GLfloat(rgb_cmap[i * 3 + 2]));
}

#endif // _MINIMOCAS_COLOR_PALETTE_HPP_
