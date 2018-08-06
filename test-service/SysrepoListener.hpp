#pragma once

#include <sysrepo.h>
#include <sysrepo/values.h>

class SysrepoListener
{
public:
    void listen();

    sr_session_ctx_t *m_session = nullptr;
private:
    void sysrepoConnect();
    int attemptSysrepoConnect();
    int subscribeToAll();
    static int changeTrampoline(sr_session_ctx_t *session,
                                const char *module,
                                sr_notif_event_t event,
                                void *data);
    int handleChanges(sr_session_ctx_t *session,
                      const char *module,
                      sr_notif_event_t event);

    sr_conn_ctx_t *m_connection = nullptr;
    sr_subscription_ctx_t *m_subscription = nullptr;
};
