#! /bin/sh

wget https://dl.bintray.com/boostorg/release/1.68.0/source/boost_1_68_0.tar.gz > /dev/null
tar zxf boost_1_68_0.tar.gz
cd boost_1_68_0
./bootstrap.sh --with-toolset=clang --prefix=$HOME/boost --with-libraries=system
./b2 install toolset=clang cxxflags="-std=c++14 -stdlib=libc++" linkflags="-stdlib=libc++" cxxstd=14 > /dev/null
cd ..
