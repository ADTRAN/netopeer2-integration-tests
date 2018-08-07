#pragma once

#include "SysrepoListener.hpp"

#include <pistache/http.h>
#include <pistache/router.h>
#include <pistache/endpoint.h>
#include <rapidjson/rapidjson.h>
#include <rapidjson/document.h>

#include <memory>

class RequestHandler
{
public:
    RequestHandler(SysrepoListener &sysrepo);

    void sendNotification(const Pistache::Rest::Request &request,
                          Pistache::Http::ResponseWriter response);
    void setActionReply(const Pistache::Rest::Request &request,
                        Pistache::Http::ResponseWriter response);
private:
    Pistache::Http::Endpoint m_endpoint;
    Pistache::Rest::Router m_router;

    SysrepoListener &m_sysrepo;
};

std::unique_ptr<SysrepoValues> parseValueList(const rapidjson::Value &parsedValues);
