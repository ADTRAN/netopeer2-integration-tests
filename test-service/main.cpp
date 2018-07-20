#include <sysrepo.h>
#include <unistd.h>
#include <iostream>

#define SR_TRY(x)                                                               \
    do {                                                                        \
        int rc = x;                                                             \
        if(rc != SR_ERR_OK) {                                                   \
            std::cerr << "sysrepo command failed: " << sr_strerror(rc) << "\n"; \
            return rc;                                                          \
        }                                                                       \
    } while(false)

class SysrepoListener
{
public:
    void listen()
    {
        sysrepoConnect();
        subscribeToAll();
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

    while(true)
    {
        pause();
    }
    return 0;
}
