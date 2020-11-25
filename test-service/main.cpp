#include "RequestHandler.hpp"
#include "SysrepoListener.hpp"

#include <unistd.h>

int main(int, char **) {
  SysrepoListener l;
  std::cout << "test-service: trying to connect to sysrepo" << std::endl;
  l.listen();

  std::cout << "test-service: connected to sysrepo, starting request-handler" << std::endl;

  RequestHandler handler(l);

  while (true) {
    pause();
  }
  return 0;
}
