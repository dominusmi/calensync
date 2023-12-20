import { BackendModule } from 'i18next';

function recursiveLoad(language: string, namespace: string, callback: any) {
    import(`../locales/${language}/${namespace}.json`).then(
        (obj) => {
            callback(null, obj);
        }
    ).catch((e) => {
        if (language.includes("-")) {
            recursiveLoad(language.split("-")[0], namespace, callback);
        } else {
            recursiveLoad("en", namespace, callback);
        }
    });
}


const LocalesImportPlugin: BackendModule = {
    type: 'backend',
    init: function (services, backendOptions, i18nextOptions) {
    },
    read: function (language, namespace, callback) {
        recursiveLoad(language, namespace, callback);
    },

    save: function (language, namespace, data) {
    },

    create: function (languages, namespace, key, fallbackValue) {
        /* save the missing translation */
    },
};

export default LocalesImportPlugin;