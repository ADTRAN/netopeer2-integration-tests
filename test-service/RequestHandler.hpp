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
private:
    Pistache::Http::Endpoint m_endpoint;
    Pistache::Rest::Router m_router;

    SysrepoListener m_sysrepo;
};

struct SysrepoValues
{
    sr_val_t *values;
    size_t valueCount;

    inline ~SysrepoValues()
    {
        sr_free_values(values, valueCount);
    }
};

std::unique_ptr<SysrepoValues> parseValueList(const rapidjson::Value &parsedValues);
