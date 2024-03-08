import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import commonjs from '@rollup/plugin-commonjs';
import { cjsInterop } from "vite-plugin-cjs-interop";

// https://vitejs.dev/config/
export default defineConfig({
    base: process.env.BASE_URL ?? "/",
    plugins: [
        react(),
        commonjs({
            include: /node_modules/,
        }),
        cjsInterop({
            dependencies: [
                "react-loader-spinner"
            ]
        })
    ],
    build:{
        commonjsOptions: { include: [] }
    },
    ssgOptions: {
        onPageRendered: (route, renderedHTML, appCtx) => {
            // We set the canonical based on the route. For all cases except /en, it's the same url (without trailing /)
            return renderedHTML.replace("%CANONICAL%", `https://calensync.live${route}`.replace(/\/$/, '').replace("/en", ""))
        },
        dirStyle: 'nested'
    }
})
