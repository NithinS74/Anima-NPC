if(NOT TARGET fmt::fmt)
  message(FATAL_ERROR "Configure AnimaConnector as the parent project")
endif()
set(fmt_FOUND TRUE)
