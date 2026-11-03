if(NOT TARGET Microsoft::DirectXMath)
  message(FATAL_ERROR "Anima must add the pinned DirectXMath target first")
endif()
set(directxmath_FOUND TRUE)
