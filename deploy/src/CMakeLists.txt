set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
add_library(openem 
  find_ruler.cc 
  detect.cc
  classify.cc
  count.cc
  util.cc 
  model.cc
  video.cc
  image.cc)
target_include_directories(openem PUBLIC 
  ${PROJECT_SOURCE_DIR}/deploy/include
  ${OpenCV_INCLUDE_DIRS})
target_link_libraries(openem
  PUBLIC
  tensorflow
  ${OpenCV_LIBS})
install(TARGETS openem
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin)

