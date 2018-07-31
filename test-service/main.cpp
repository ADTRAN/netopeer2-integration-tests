#include <sysrepo.h>
#include <sysrepo/values.h>
#include <unistd.h>
#include <iostream>
#include <fstream>
#include <string>
#include <sstream>

#include <pistache/http.h>
#include <pistache/router.h>
#include <pistache/endpoint.h>

#include <rapidjson/rapidjson.h>
#include <rapidjson/document.h>
#include <rapidjson/error/en.h>
#include <rapidjson/error/error.h>

#define SR_TRY(x)                                                               \
    do {                                                                        \
        int rc = x;                                                             \
        if(rc != SR_ERR_OK) {                                                   \
            std::cerr << "sysrepo command failed: " << sr_strerror(rc) << "\n"; \
            return rc;                                                          \
        }                                                                       \
    } while(false)

namespace std
{
std::string to_string(sr_notif_event_t e)
{
    switch(e)
    {
    case SR_EV_VERIFY:
        return "SR_EV_VERIFY";
    case SR_EV_APPLY:
        return "SR_EV_APPLY";
    case SR_EV_ABORT:
        return "SR_EV_ABORT";
    case SR_EV_ENABLED:
        return "SR_EV_ENABLED";
    }
}

std::string to_string(sr_change_oper_t c)
{
    switch(c)
    {
    case SR_OP_CREATED:
        return "SR_OP_CREATED";
    case SR_OP_MODIFIED:
        return "SR_OP_MODIFIED";
    case SR_OP_DELETED:
        return "SR_OP_DELETED";
    case SR_OP_MOVED:
        return "SR_OP_MOVED";
    }
}
}

class SysrepoListener
{
public:
    void listen()
    {
        sysrepoConnect();
        subscribeToAll();
    }

    void sendNotification(const Pistache::Rest::Request &request,
                          Pistache::Http::ResponseWriter response)
    {
        rapidjson::Document d;
        rapidjson::ParseResult parseResult = d.Parse(request.body().c_str());
        if(!parseResult)
        {
            std::ostringstream oss;
            oss << "Failed to parse JSON document: " << GetParseError_En(parseResult.Code());
            response.send(Pistache::Http::Code::Bad_Request, oss.str());
            return;
        }

        if(!d.HasMember("xpath"))
        {
            response.send(Pistache::Http::Code::Bad_Request, "Missing xpath field");
            return;
        }

        if(!d.HasMember("values"))
        {
            response.send(Pistache::Http::Code::Bad_Request, "Missing values field");
            return;
        }

        const auto &parsedValues = d["values"];

        sr_val_t *values;
        int valueCount = parsedValues.Size();
        sr_new_values(valueCount, &values);
        bool error = false;
        for(int i = 0; i < valueCount; ++i)
        {
            if(!parsedValues[i].HasMember("xpath"))
            {
                response.send(Pistache::Http::Code::Bad_Request, "Missing xpath field");
                error = true;
            }

            if(!parsedValues[i].HasMember("value"))
            {
                response.send(Pistache::Http::Code::Bad_Request, "Missing value field");
                error = true;
            }

            sr_val_set_xpath(values + i, parsedValues[i]["xpath"].GetString());
            sr_val_set_str_data(values + i, SR_STRING_T, parsedValues[i]["value"].GetString());
        }
        sr_free_values(values, valueCount);

        int ret = sr_event_notif_send(m_session, d["xpath"].GetString(), values, valueCount, SR_EV_NOTIF_DEFAULT);
        if(ret != SR_ERR_OK)
        {
            response.send(Pistache::Http::Code::Bad_Request, "Failed to send request to sysrepo");
        }
        else if(!error)
        {
            response.send(Pistache::Http::Code::Ok, "Notification sent");
        }
    }
private:
    void sysrepoConnect()
    {
        while(attemptSysrepoConnect() != SR_ERR_OK)
        {
            usleep(1000 * 1000 * 1);
        }
    }

    int attemptSysrepoConnect()
    {
        SR_TRY(sr_connect("test_service",
                          SR_CONN_DAEMON_REQUIRED,
                          &m_connection));
        SR_TRY(sr_session_start(m_connection,
                                SR_DS_RUNNING,
                                SR_SESS_CONFIG_ONLY,
                                &m_session));
        return SR_ERR_OK;
    }
    int subscribeToAll()
    {
        sr_schema_t *schemas;
        size_t schemaCount;
        SR_TRY(sr_list_schemas(m_session, &schemas, &schemaCount));

        for(sr_schema_t *schema = schemas; (size_t)(schema - schemas) < schemaCount; schema++)
        {
            std::cerr << "Subscribing to module " << schema->module_name << "\n";
            if(sr_module_change_subscribe(m_session,
                                          schema->module_name,
                                          changeTrampoline,
                                          (void*)this,
                                          0 /*priority*/,
                                          SR_SUBSCR_CTX_REUSE | SR_SUBSCR_EV_ENABLED,
                                          &m_subscription))
            {
                std::cerr << "Failed to subscribe to " << schema->module_name << "\n";
            }
            else
            {
                std::cerr << "Subscribed to module " << schema->module_name << "\n";
            }
        }
        sr_free_schemas(schemas, schemaCount);

        return SR_ERR_OK;
    }

    static int changeTrampoline(sr_session_ctx_t *session,
                                const char *module,
                                sr_notif_event_t event,
                                void *data)
    {
        return ((SysrepoListener*)data)->handleChanges(session, module, event);
    }

    int handleChanges(sr_session_ctx_t *session,
                      const char *module,
                      sr_notif_event_t event)
    {
        std::ofstream events("/tmp/test-service-event-stream.yml",
                             std::ios::out | std::ios::app | std::ios::ate);
        if(!events)
        {
            std::cerr << "Failed to open event log file\n";
            return SR_ERR_OPERATION_FAILED;
        }
        std::ostringstream selector;
        selector << "/" << module << ":*";
        sr_change_iter_t *iter;
        SR_TRY(sr_get_changes_iter(session, selector.str().c_str(), &iter));

        events << "---\n";
        events << "event_type: " << std::to_string(event) << "\n";
        events << "values:\n";

        sr_val_t *old;
        sr_val_t *new_;
        sr_change_oper_t op;
        while(sr_get_change_next(session, iter, &op, &old, &new_) == SR_ERR_OK)
        {
            events << "  - operation: " << std::to_string(op) << "\n";
            if(old)
            {
                events << "    old-path: " << old->xpath << "\n";
                char *v = sr_val_to_str(old);
                events << "    old-value: " << v << "\n";
                free(v);
            }

            if(new_)
            {
                events << "    new-path: " << new_->xpath << "\n";
                char *v = sr_val_to_str(new_);
                events << "    new-value: " << v << "\n";
                free(v);
            }
        }

        sr_free_change_iter(iter);

        return SR_ERR_OK;
    }

    sr_conn_ctx_t *m_connection = nullptr;
    sr_session_ctx_t *m_session = nullptr;
    sr_subscription_ctx_t *m_subscription = nullptr;
};

int main(int, char**)
{
    SysrepoListener l;
    l.listen();

    Pistache::Rest::Router router;
    Pistache::Rest::Routes::Post(router, "/send-notification",
                                 Pistache::Rest::Routes::bind(&SysrepoListener::sendNotification, &l));
    Pistache::Http::Endpoint endpoint("*:9080");
    endpoint.init(Pistache::Http::Endpoint::options().threads(1));
    endpoint.setHandler(router.handler());
    endpoint.serve();

    while(true)
    {
        pause();
    }
    return 0;
}
