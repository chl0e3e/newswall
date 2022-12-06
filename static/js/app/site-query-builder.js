define(["jquery", "materialize", "uuidv4"], function($, materialize, uuidv4) {
    const ADD_ICON = "<i class=\"material-icons\">add</i>";
    const ADD_ICON_LEFT = "<i class=\"material-icons left\">add</i>";
    const ADD_CIRCLE_ICON_LEFT = "<i class=\"material-icons left\">add_circle</i>";

    const REMOVE_ICON_LEFT = "<i class=\"material-icons left\">remove</i>";
    const REMOVE_CIRCLE_ICON_LEFT = "<i class=\"material-icons left\">remove_circle</i>";

    const EDIT_ICON = "<i class=\"material-icons\">edit</i>";
    const REMOVE_ICON = "<i class=\"material-icons\">remove</i>";

    const OPERATORS = {
        "equals": "Equals",
        "contains": "Contains"
        //"is_null": "Is Null",
        //"is_not_null": "Is Not Null"
    };

    let components = {};

    function initMaterialize(el) {    
        el.find("select").formSelect();
        el.find('.tooltipped').tooltip();
        try {
            el.find(".dropdown-trigger").dropdown({
                constrainWidth: false
            });
        } catch (e) {

        }
    }

    class Root {
        constructor(id, siteData) {
            console.log("Root");
            this.id = id;
            this.siteData = siteData;
            this.group = new RootGroup(this, uuidv4());
            this.html = $("<div></div>")
                .attr("id", this.id)
                .attr("class", "query-builder");
            this.html.append(this.group.render());
        }
        
        render() {
            return this.html;
        }

        filters(site) {
            return this.siteData[site]["keys"];
        }
    }

    class Rule {
        constructor(parent, id, filters) {
            this.parent = parent;
            this.id = id;
            this.filters = filters;
            this.children = [];
            
            this.html = $("<div></div>")
                .attr("id", id)
                .attr("class", "rule-container");

            this.html.append(this.renderRuleHeader());
            this.html.append(this.renderRuleBody());
            this.html.append(this.renderRuleChildren());
        }

        renderRuleHeader() {
            const rule = this;

            this.header = $("<div></div>")
                .attr("class", "rule-header");

            let dropdownID = uuidv4();
            let removeButton = $("<button></button>")
                .attr("type", "button")
                .attr("class", "btn-floating btn-small waves-effect waves-light red dropdown-trigger")
                .attr("data-target", dropdownID)
                .html(REMOVE_ICON)
                .click(function(e) {
                    rule.btnRemove(e);
                });
            
            this.header.append(removeButton);

            return this.header;
        }

        renderRuleBody() {
            let filterContainer = $("<div></div>")
                .attr("class", "rule-filter-container");
            this.filter = $("<select></select>")
                .attr("name", this.id + "_filter");
            for (var filterKey in this.filters) {
                let filterOption = $("<option></option>")
                    .attr("value", filterKey)
                    .text(this.filters[filterKey]);

                this.filter.append(filterOption);
            }
            filterContainer.append(this.filter);

            let operatorContainer = $("<div></div>")
                .attr("class", "rule-operator-container");
            this.operator = $("<select></select>")
                .attr("name", this.id + "_operator");
            for (var operatorKey in OPERATORS) {
                let operatorOption = $("<option></option>")
                    .attr("value", operatorKey)
                    .text(OPERATORS[operatorKey]);

                this.operator.append(operatorOption);
            }
            operatorContainer.append(this.operator);

            let valueContainer = $("<div></div>")
                .attr("class", "rule-value-container");
            this.value = $("<input />")
                .attr("type", "text")
                .attr("value", "")
                .attr("name", this.id + "_value");
            valueContainer.append(this.value);
            
            return $("<div></div>")
                .attr("class", "rule-body")
                .append(filterContainer)
                .append(operatorContainer)
                .append(valueContainer);
        }

        renderRuleChildren() {
            this.childrenEl = $("<div></div>")
                .attr("class", "rule-children");
            for(var childIndex in this.children) {
                var child = this.children[childIndex];
                this.childrenEl.append(child.render());
            }
            return this.childrenEl;
        }

        render() {
            return this.html;
        }

        btnRemove(e) {
            console.log("btnRemove");
            console.log(e);
            this.parent.remove(this);
            this.html.remove();
        }

        btnAddGroup(e) {
            console.log("btnAddGroup");
            console.log(e);
            let group = new Group(this, uuidv4(), this.filters);
            this.children.push(group);
            this.childrenEl.append(group.render());
        }

        remove(rule) {
            this.children.splice(this.children.indexOf(rule), 1);
        }
    }

    class RootRule extends Rule {
        constructor(parent, id, filters) {
            super(parent, id, filters);

            this.hasGroup = false;
            this.html.addClass("blue-grey").addClass("lighten-3").addClass("root-rule");
        }

        renderRuleHeader() {
            const rule = this;

            this.header = $("<div></div>")
                .attr("class", "rule-header");

            let dropdownID = uuidv4();
            let menuButton = $("<button></button>")
                .attr("type", "button")
                .attr("class", "btn-floating btn-small waves-effect waves-light red dropdown-trigger")
                .attr("data-target", dropdownID)
                .html(EDIT_ICON);

            let editMenu = $("<ul></ul>")
                .attr("class", "dropdown-content")
                .attr("id", dropdownID);

            let editAddGroupItem = $("<li></li>");
            this.editAddGroupItemLink = $("<a></a>")
                .attr("href", "#!")
                .text("Add Group")
                .click(function(e) {
                    rule.btnAddGroup(e);
                });
            editAddGroupItem.append(this.editAddGroupItemLink);
                
            let editRemoveItem = $("<li></li>");
            let editRemoveItemLink = $("<a></a>")
                .attr("href", "#!")
                .text("Remove")
                .click(function(e) {
                    rule.btnRemove(e);
                });
            editRemoveItem.append(editRemoveItemLink);

            editMenu.append(editRemoveItem);
            editMenu.append(editAddGroupItem);
            
            this.header.append(menuButton);
            this.header.append(editMenu);

            return this.header;
        }

        renderRuleBody() {
            console.log("renderRuleBody - Root");

            let filterContainer = $("<div></div>")
                .attr("class", "rule-filter-container");
            this.filter = $("<select></select>")
                .attr("name", this.id + "_filter")
                .attr("disabled", "disabled");
            let siteOption = $("<option></option>")
                .attr("value", "site")
                .text("Site");
            this.filter.append(siteOption);
            filterContainer.append(this.filter);

            let operatorContainer = $("<div></div>")
                .attr("class", "rule-operator-container");
            this.operator = $("<select></select>")
                .attr("name", this.id + "_operator")
                .attr("disabled", "disabled");
            let operatorOption = $("<option></option>")
                .attr("value", "equals")
                .text("equals");
            this.operator.append(operatorOption);
            operatorContainer.append(this.operator);

            let valueContainer = $("<div></div>")
                .attr("class", "rule-value-container");
            this.value = $("<select></select>")
                .attr("type", "text")
                .attr("value", "")
                .attr("class", "red")
                .attr("name", this.id + "_value");
            for (var siteID in this.parent.parent.siteData) {
                let valueOption = $("<option></option>")
                    .attr("value", siteID)
                    .text(this.parent.parent.siteData[siteID]["name"]);

                this.value.append(valueOption);
            }
            valueContainer.append(this.value);
            
            return $("<div></div>")
                .attr("class", "rule-body")
                .append(filterContainer)
                .append(operatorContainer)
                .append(valueContainer);
        }

        btnAddGroup(e) {
            if(this.hasGroup) {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            console.log("btnAddGroup");
            console.log(e);
            let group = new Group(this, uuidv4(), this.parent.parent.filters(this.value.val()));
            this.children.push(group);
            this.childrenEl.append(group.render());
            this.setHasGroup(true);
        }

        setHasGroup(val) {
            console.log("setHasGroup");
            this.hasGroup = val;
            if (val) {
                this.editAddGroupItemLink.addClass("disabled");
            } else {
                this.editAddGroupItemLink.removeClass("disabled");
            }
        }
    }

    class Group {
        constructor(parent, id, filters) {
            this.parent = parent;
            this.id = id;
            this.filters = filters;

            this.children = [];

            this.html = $("<div></div>")
                .attr("id", this.id)
                .attr("class", "rules-group-container");

            console.log("Group");
            console.log(this.parent);
            console.log("Group end");

            this.html.append(this.renderHeader());
            this.html.append(this.renderBody());
        }
        
        renderHeader() {
            console.log("renderHeader");

            this.header = $("<div></div>")
                .attr("class", "rules-group-header");

            let actions = this.renderActions();
            let conditions = this.renderConditions();

            return this.header.append(actions).append(conditions);
        }

        renderActions() {
            const group = this;

            let actionsGroup = $("<div></div>")
                .attr("class", "group-actions");

            let addRuleButton = $("<button></button>")
                .attr("type", "button")
                .attr("class", "waves-effect waves-light btn btn-small light-green")
                .html(ADD_ICON_LEFT + "Rule")
                .click(function(e) {
                    group.btnAddRule(e);
                });

            let addGroupButton = $("<button></button>")
                .attr("type", "button")
                .attr("class", "waves-effect waves-light btn btn-small green")
                .html(ADD_ICON_LEFT + "Group")
                .click(function(e) {
                    group.btnAddGroup(e);
                });

            let removeButton = $("<button></button>")
                .attr("type", "button")
                .attr("class", "waves-effect waves-light btn btn-small red")
                .html(REMOVE_ICON_LEFT + "Remove")
                .click(function(e) {
                    group.btnRemove(e);
                });

            actionsGroup.append(addRuleButton).append(addGroupButton).append(removeButton);
            
            return actionsGroup;
        }

        renderConditions() {
            let conditionsGroup = $("<div></div>")
                .attr("class", "group-conditions");

            this.andButtonRadio = $("<input />")
                .attr("type", "radio")
                .attr("checked", "checked")
                .attr("name", this.id + "_condition")
                .attr("value", "AND");
            let andButtonSpan = $("<span></span>")
                .text("AND");
            let andButtonLabel = $("<label></label>")
                .attr("class", "cond-and")
                .append(this.andButtonRadio)
                .append(andButtonSpan);
            conditionsGroup.append(andButtonLabel);
            
            this.orButtonRadio = $("<input />")
                .attr("type", "radio")
                .attr("name", this.id + "_condition")
                .attr("value", "OR");
            let orButtonSpan = $("<span></span>")
                .text("OR");
            let orButtonLabel = $("<label></label>")
                .attr("class", "cond-or")
                .append(this.orButtonRadio)
                .append(orButtonSpan);
            conditionsGroup.append(orButtonLabel);

            return conditionsGroup;
        }

        renderBody() {
            console.log("renderBody");
            let body = $("<div></div>")
                .attr("class", "rules-group-body");
            this.rulesList = $("<div></div>")
                .attr("class", "rules-list");
            body.append(this.rulesList);
            return body;
        }

        render() {
            return this.html;
        }

        btnAddRule(e) {
            console.log("btnAddRule");
            console.log(e);
            console.log(this);

            let rule = new Rule(this, uuidv4(), this.filters);
            this.children.push(rule);
            this.rulesList.append(rule.render());
            initMaterialize(rule.html);
        }

        btnAddGroup(e) {
            console.log("btnAddGroup");
            console.log(e);
            console.log(this);

            let group = new Group(this, uuidv4(), this.filters);
            this.children.push(group);
            this.rulesList.append(group.render());
        }

        btnRemove(e) {
            console.log("btnRemove");
            console.log(e);
            console.log(this);

            this.parent.remove(this);
            this.html.remove();
            if(this.parent instanceof RootRule) {
                this.parent.setHasGroup(false);
            }
        }

        remove(rule) {
            this.children.splice(this.children.indexOf(rule), 1);
        }
    }

    class RootGroup extends Group {
        constructor(parent, id, filters) {
            super(parent, id, filters);

            console.log("RootGroup " + id);
            console.log(this.rulesList);
        }

        renderActions() {
            const group = this;

            let actionsGroup = $("<div></div>")
                .attr("class", "group-actions");

            let addSiteButton = $("<button></button>")
                .text("Add Site")
                .attr("type", "button")
                .attr("class", "btn-floating btn waves-effect waves-light blue dropdown-trigger tooltipped")
                .attr("data-position", "right")
                .attr("data-tooltip", "Add Site")
                .html(ADD_ICON)
                .click(function(e) {
                    group.btnAddRule(e);
                });

            return actionsGroup.append(addSiteButton);
        }

        renderConditions() {
            return $("<div></div>");
        }

        btnAddRule(e) {
            console.log("btnAddRule - RootGroup");
            console.log(e);
            console.log(this);

            let rule = new RootRule(this, uuidv4(), []);
            this.children.push(rule);
            this.rulesList.append(rule.render());
            initMaterialize(rule.html);
        }
    }

    return class SiteQueryBuilder {
        constructor(id, siteData) {
            this.id = id;
            this.root = new Root(id, siteData);

            var self = this;
            this.postRender = function() {
                initMaterialize($("#" + self.id));
            };
        }

        render() {
            return this.root.render();
        }

        query() {
            function traverse(element) {
                let tree = {
                    "type": (element instanceof Group ? "group" : "rule"),
                    "children": [],
                };

                if (element instanceof Rule) {
                    tree["filter"] = element.filter.val();
                    tree["operator"] = element.operator.val();
                    tree["value"] = element.value.val();
                } else if (element instanceof RootGroup) {
                    tree["type"] = "root";
                } else if (element instanceof Group) {
                    tree["condition"] = element.andButtonRadio.prop('checked') ? "AND" : "OR";
                }

                let elementChildren = element.children;
                for(var childKey in element.children) {
                    var child = element.children[childKey];
                    tree["children"].push(traverse(child));
                }

                return tree;
            }

            return traverse(this.root.group);
        }
    }
});