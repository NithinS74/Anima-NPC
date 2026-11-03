if(NOT TARGET Microsoft::DirectXTK)
  message(FATAL_ERROR "Anima must add the pinned DirectXTK target first")
endif()
set(directxtk_FOUND TRUE)
