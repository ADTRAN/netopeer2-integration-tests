#include "SysrepoListener.hpp"

#include <sysrepo/xpath.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string.h>
#include <string>
#include <functional>
#include <unistd.h>

#define SR_TRY(x)                                                              \
  do {                                                                         \
    int rc = x;                                                                \
    if (rc != SR_ERR_OK) {                                                     \
      std::cerr << "sysrepo command failed: " << sr_strerror(rc) << "\n";      \
      return rc;                                                               \
    }                                                                          \
  } while (false)

using std::to_string;

class XpathVector : public std::vector<std::string>
{
public:
    void walk(const struct lys_node *node, std::function<bool(const struct lys_node*)> pred)
    {
        for(const struct lys_node *n = node; n; n=n->next)
        {
            if ( pred(n) ) {
                char *path = lys_path(n, LYS_PATH_FIRST_PREFIX);
                if ( path && !strstr(path, "{grouping}[") && !strstr(path, "{augment}[") ) {
                    strip_dup_ns(path);
                    push_back(path);
                }
                else {
                    free(path);
                }
                continue;
            }
            if ( ! (n->nodetype & (LYS_LEAF | LYS_LEAFLIST | LYS_ANYDATA )) ) {
                walk(n->child, pred);
            }
        }
    }
private:
    char *get_next_slash(char *path) {
        bool q = false, qq = false;
        while (*path && (q || qq || *path != '/')) {
           if (*path == '\'') {
               q = !q;
           }
           else if (*path == '"') {
               qq = !qq;
           }
           ++path;
        }
        return path;
    }
    char *get_next_ns(char *expr)
    {
        int i;
        while (*expr) {
            expr = get_next_slash(expr);
            if (expr[0] != '/') {
                return NULL;
            }
            if (!isalpha(expr[1]) && (expr[1] != '_')) {
                ++expr;
                continue;
            }
            for (i = 2; expr[i] && (isalnum(expr[i]) || (expr[i] == '_') || (expr[i] == '-') || (expr[i] == '.')); ++i) {}
            if (expr[i] != ':') {
                ++expr;
                continue;
            }
            return strndup(expr, i+1);
        }
    }
    void strip_dup_ns(char *path)
    {
        char *ns, *p0, *p, *q;
        while (ns = get_next_ns(path)) {
            p0 = strstr(path, ns);
            if (p0) {
                while (p0 = strstr(p0+strlen(ns), ns)) {
                    p = p0+1;
                    q = p0+strlen(ns);
                    while (*p++ = *q++) {}
                }
            }
            path += strlen(ns);
            free(ns);
        }
    }
};



std::string to_string(sr_event_t e) {
  switch (e) {
  case SR_EV_UPDATE : 
    return "SR_EV_UPDATE";
  case SR_EV_CHANGE : 
    return "SR_EV_CHANGE";
  case SR_EV_DONE : 
    return "SR_EV_DONE";
  case SR_EV_ABORT : 
    return "SR_EV_ABORT";
  case SR_EV_ENABLED : 
    return "SR_EV_ENABLED";
  case SR_EV_RPC : 
    return "SR_EV_RPC";
  }
  return "SR_EV_INVALID";
}

std::string to_string(sr_change_oper_t c) {
  switch (c) {
  case SR_OP_CREATED:
    return "SR_OP_CREATED";
  case SR_OP_MODIFIED:
    return "SR_OP_MODIFIED";
  case SR_OP_DELETED:
    return "SR_OP_DELETED";
  case SR_OP_MOVED:
    return "SR_OP_MOVED";
  }
  return "SR_OP_INVALID";
}

static void my_sr_log_cb(sr_log_level_t level, const char *msg)
{
      std::cerr << "sysrepo(" << level << ") " << msg << "\n"; 
}

SysrepoListener::SysrepoListener() {
    sr_log_set_cb(my_sr_log_cb);
}

void SysrepoListener::listen() {
  sysrepoConnect();
  subscribeToAll();
}

void SysrepoListener::sysrepoConnect() {
  while (attemptSysrepoConnect() != SR_ERR_OK) {
    usleep(1000 * 1000 * 1);
  }
}

int SysrepoListener::attemptSysrepoConnect() {
  SR_TRY(sr_connect(SR_CONN_DEFAULT, &m_connection));
  SR_TRY(sr_session_start(m_connection, SR_DS_RUNNING, &m_session));
  return SR_ERR_OK;
}
  
const struct ly_ctx *SysrepoListener::getLyCtx() const {

    if(m_session) {
        return sr_get_context(sr_session_get_connection(m_session));
    }
    return nullptr;
}

std::vector<std::string> SysrepoListener::get_action_xpathes() const
{
    XpathVector xpathVector;

    uint32_t idx = 0;
    const struct lys_module *module = nullptr;
    while( (module = ly_ctx_get_module_iter(getLyCtx(), &idx)) ) {
        xpathVector.walk(module->data,
                        [](const struct lys_node*n){return n->nodetype==LYS_ACTION;});
    }
    return xpathVector;
}

std::vector<std::string> SysrepoListener::get_config_modules() const {
    std::vector<std::string> retvec;
    uint32_t idx = 0;
    const struct lys_module *module = nullptr;
    // collect all modules that have a top-level element with config=true
    while( (module = ly_ctx_get_module_iter(getLyCtx(), &idx)) ) {
        for(const struct lys_node *n=module->data; n; n=n->next) {
            if ( n->nodetype & (LYS_CONTAINER | LYS_LIST | LYS_LEAF | LYS_LEAFLIST) ) {
                if ( n->flags & LYS_CONFIG_W ) {
                    retvec.push_back(module->name);
                    break;
                }
            }
        }
    }
    return retvec;
}


int SysrepoListener::subscribeToAll() {

  for(const std::string &module: get_config_modules())
  {
    std::cerr << "Subscribing to module " << module.c_str() << "\n";
    if(sr_module_change_subscribe(m_session,
                                  module.c_str(),
                                  NULL, /*xpath*/
                                  changeTrampoline,
                                  (void*)this,
                                  0     /*priority*/,
                                  SR_SUBSCR_CTX_REUSE | SR_SUBSCR_ENABLED,
                                  &m_subscription)) 
    {
      std::cerr << "Failed to subscribe to " << module << "\n"; 
    } 
    else
    {
      std::cerr << "Subscribed to module " << module << "\n";
      const struct lys_module *ly_mod = ly_ctx_get_module(getLyCtx(), module.c_str(), NULL, 1);
      m_module2Schema[module] = ly_mod ? ly_mod->data->name : "";
    }
  } 

  for(const std::string &xpath: get_action_xpathes())
  { 
    std::cerr << "Subscribing to xpath " << xpath << "\n";
    if(sr_rpc_subscribe_tree(m_session,
                             xpath.c_str(),
                             &SysrepoListener::actionTrampoline,
                             this,
                             0 /*priority*/,
                             SR_SUBSCR_CTX_REUSE,
                             &m_subscription) != SR_ERR_OK)
    {
      std::cerr << "Failed to subscribe to " << xpath << "\n"; 
    } 
    else
    {
      std::cerr << "Subscribed to xpath " << xpath << "\n";
    }
    m_subscribedActions.insert(xpath);
  }
  return SR_ERR_OK;
}

int SysrepoListener::changeTrampoline(sr_session_ctx_t *session,
                                      const char *module,
                                      const char *xpath,
                                      sr_event_t event,
                                      uint32_t request_id,
                                      void *data) {

  return ((SysrepoListener *)data)->handleChanges(session, module, event);
}

int SysrepoListener::handleChanges(sr_session_ctx_t *session,
                                   const char *module, sr_event_t event) {
  std::ofstream events("/tmp/test-service-event-stream.yml",
                       std::ios::out | std::ios::app | std::ios::ate);
  if (!events) {
    std::cerr << "Failed to open event log file\n";
    return SR_ERR_OPERATION_FAILED;
  }
  std::ostringstream selector;
  if (m_module2Schema[module].empty()) {
    selector << "/" << module << ":*";
  }
  else {
    selector << "/" << module << ":" << m_module2Schema[module] << "/*";
  }
  sr_change_iter_t *iter;
  SR_TRY(sr_get_changes_iter(session, selector.str().c_str(), &iter));

  events << "---\n";
  events << "event_type: " << to_string(event) << "\n";
  events << "values:\n";

  sr_val_t *old;
  sr_val_t *new_;
  sr_change_oper_t op;
  while (sr_get_change_next(session, iter, &op, &old, &new_) == SR_ERR_OK) {
    events << "  - operation: " << to_string(op) << "\n";
    if (old) {
      events << "    old-path: " << old->xpath << "\n";
      char *v = sr_val_to_str(old);
      events << "    old-value: " << v << "\n";
      free(v);
    }

    if (new_) {
      events << "    new-path: " << new_->xpath << "\n";
      char *v = sr_val_to_str(new_);
      events << "    new-value: " << v << "\n";
      free(v);
    }
  }

  sr_free_change_iter(iter);

  return SR_ERR_OK;
}

bool SysrepoListener::subscribeForAction(const char *xpath) {
  std::string key(xpath);
  if (m_subscribedActions.find(key) != m_subscribedActions.end()) {
    // Already subscribed
    return true;
  }

  if(sr_rpc_subscribe_tree(m_session,
                           xpath,
                           &SysrepoListener::actionTrampoline,
                           this,
                           0 /*priority*/,
                           SR_SUBSCR_CTX_REUSE,
                           &m_subscription) != SR_ERR_OK) {
    return false; 
  }

  m_subscribedActions.insert(key);
  return true;
}

static std::string xpathToSchemaPath(const char *xpath) {
  char *mutableXpath = strdup(xpath);
  sr_xpath_ctx_t ctx;
  bzero(&ctx, sizeof(ctx));
  std::ostringstream oss;

  for (char *node = sr_xpath_next_node_with_ns(mutableXpath, &ctx); node;
       node = sr_xpath_next_node(nullptr, &ctx)) {
    oss << "/" << node;
  }
  std::free(mutableXpath);
  return oss.str();
}

void SysrepoListener::setActionValues(const char *xpath,
                                      std::unique_ptr<SysrepoValues> &&values) {
  std::string schema(xpathToSchemaPath(xpath));
  m_actionValues[schema] = std::move(values);
}

int SysrepoListener::actionTrampoline(sr_session_ctx_t *session,
                                      const char *xpath,
                                      const struct lyd_node *input,
                                      sr_event_t event,
                                      uint32_t request_id,
                                      struct lyd_node *output,
                                      void *data)
{
  return ((SysrepoListener *)data)->handleAction(session, xpath, input, output);
}

int SysrepoListener::handleAction(sr_session_ctx_t *session, const char *xpath, const struct lyd_node *input, struct lyd_node *output) 
{
  std::string schemaPath(xpathToSchemaPath(xpath));

  auto values = m_actionValues.find(schemaPath);
  if (values == m_actionValues.end()) {
    std::cerr << "Unexpected action at XPath " << xpath << " (schema path "
              << schemaPath << ")\n";
    return SR_ERR_INTERNAL;
  }
  lyd_new_output_leaf(output, lys_node_module(output->schema), "action-output", values->second->values->data.string_val);
  return SR_ERR_OK;
}
