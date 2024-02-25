import { BlogLanguageWrapper, BlogProperties, RouteWrapper } from "reactyll";
import { ExtraProperties } from "../components/BlogTemplate";

export function sortBlogsByDate(blogs: RouteWrapper<ExtraProperties>): BlogLanguageWrapper<ExtraProperties>[] {
    // Convert the blogs object to an array of entries
    const blogEntries = Object.entries(blogs);

    // Sort the entries based on the title of the first key2
    blogEntries.sort(([keyA, valueA], [keyB, valueB]) => {
        const dateA = Object.values(valueA)[0].publishDate;
        const dateB = Object.values(valueB)[0].publishDate;
        return dateB.localeCompare(dateA);
    });

    // Extract and return the sorted values (list of objects with key2 as keys)
    return blogEntries.map(([key, value]) => value);
}

export function getBlogByLanguage(wrapper: BlogLanguageWrapper<ExtraProperties>, language: string | undefined): BlogProperties & ExtraProperties {
    // Convert the blogs object to an array of entries
    if(language == null || !(language in wrapper)){
        return wrapper["en"]
    }else {
        return wrapper[language]
    }
}