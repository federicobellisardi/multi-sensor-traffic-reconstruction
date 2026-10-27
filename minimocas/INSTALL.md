# VM CONFIG - SIMULATOR

###
cmake >= 3.12
github user Ator Simul credentials (vivesimulator@gmail.com + ssh key)
mkdir ~/Codice
echo "export WORKSPACE=~/Codice" >> ~/.bashrc
. ~/.bashrc
cd ~/Codice
git clone https://github.com/physycom/sysconfig
git clone https://github.com/physycom/minimocas
cd minimocas
git submodule update --init --recursive
install libfltk1.3-dev
install libsqlite
./build.sh
