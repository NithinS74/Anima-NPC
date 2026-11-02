# The pinned parent build already owns spdlog's target.
if(NOT TARGET spdlog::spdlog)
  message(FATAL_ERROR "Configure AnimaConnector as the parent project")
endif()
set(spdlog_FOUND TRUE)
